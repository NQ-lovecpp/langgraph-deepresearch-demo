import os
from typing import Optional

from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration, get_active_provider, get_provider_config
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)
from agent.search_providers import (
    get_search_provider,
    format_exa_results_for_llm,
)

load_dotenv()

# Initialize provider-specific clients
_active_provider = get_active_provider()
_provider_config = get_provider_config()

# Google-specific client (only initialized if using Google provider)
genai_client = None
if _active_provider == "google":
    from google.genai import Client
    api_key = _provider_config.get("api_key") or os.getenv("GEMINI_API_KEY")
    if api_key:
        genai_client = Client(api_key=api_key)
    else:
        print("WARNING: Google provider selected but no GEMINI_API_KEY found")


def get_llm(model_name: str, config: Configuration, temperature: float = 1.0) -> BaseChatModel:
    """Get the appropriate LLM based on the provider configuration."""
    provider = config.provider
    
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = config.get_api_key()
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_retries=2,
            api_key=api_key,
        )
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_retries=2,
            api_key=config.get_api_key(),
            base_url=config.get_base_url(),
        )
    elif provider == "local":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_retries=2,
            api_key="not-needed",  # Local server doesn't need API key
            base_url=config.get_base_url(),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_structured_output(llm: BaseChatModel, schema, config: Configuration):
    """Get structured output from LLM with provider-specific handling."""
    import json
    from langchain_core.output_parsers import PydanticOutputParser
    
    provider = config.provider
    
    if provider == "google":
        # Google Gemini supports native structured output
        return llm.with_structured_output(schema)
    else:
        # For OpenRouter and local, use manual JSON parsing
        parser = PydanticOutputParser(pydantic_object=schema)
        
        class StructuredLLM:
            def __init__(self, llm, parser, schema):
                self.llm = llm
                self.parser = parser
                self.schema = schema
            
            def invoke(self, prompt):
                # Add JSON format instructions to the prompt
                format_instructions = f"""
You MUST respond with a valid JSON object that matches this schema:
{json.dumps(self.schema.model_json_schema(), indent=2)}

Only respond with the JSON object, no additional text or markdown formatting.
"""
                full_prompt = f"{prompt}\n\n{format_instructions}"
                response = self.llm.invoke(full_prompt)
                
                # Extract content
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract JSON from the response
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # Parse and validate
                try:
                    data = json.loads(content)
                    return self.schema(**data)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {content}")
        
        return StructuredLLM(llm, parser, schema)


# Nodes
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question.

    Uses the configured LLM to create optimized search queries for web research based on
    the User's question.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated queries
    """
    configurable = Configuration.from_runnable_config(config)

    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    # Get the appropriate LLM
    llm = get_llm(configurable.query_generator_model, configurable, temperature=1.0)
    structured_llm = get_structured_output(llm, SearchQueryList, configurable)

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    # Generate the search queries
    result = structured_llm.invoke(formatted_prompt)
    return {"search_query": result.query}


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node.

    This is used to spawn n number of web research nodes, one for each search query.
    """
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["search_query"])
    ]


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using the configured search provider.

    Executes a web search using either Google Search API or Exa based on configuration.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    configurable = Configuration.from_runnable_config(config)
    provider = configurable.provider
    
    if provider == "google":
        # Use Google's native search capability
        return _web_research_google(state, configurable)
    else:
        # Use Exa search for OpenRouter and local providers
        return _web_research_exa(state, configurable)


def _web_research_google(state: WebSearchState, configurable: Configuration) -> OverallState:
    """Web research using Google's native search API."""
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=state["search_query"],
    )

    # Uses the google genai client as the langchain client doesn't return grounding metadata
    response = genai_client.models.generate_content(
        model=configurable.query_generator_model,
        contents=formatted_prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
        },
    )
    # resolve the urls to short urls for saving tokens and time
    resolved_urls = resolve_urls(
        response.candidates[0].grounding_metadata.grounding_chunks, state["id"]
    )
    # Gets the citations and adds them to the generated text
    citations = get_citations(response, resolved_urls)
    modified_text = insert_citation_markers(response.text, citations)
    sources_gathered = [item for citation in citations for item in citation["segments"]]

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


def _web_research_exa(state: WebSearchState, configurable: Configuration) -> OverallState:
    """Web research using Exa search API."""
    # Get Exa search provider
    exa_api_key = configurable.get_exa_api_key()
    search_provider = get_search_provider(configurable.provider, exa_api_key)
    
    # Execute search
    search_results = search_provider.search(state["search_query"], num_results=5)
    
    # Format results for LLM
    formatted_text, sources = format_exa_results_for_llm(search_results, state["id"])
    
    # Use LLM to summarize the search results
    llm = get_llm(configurable.query_generator_model, configurable, temperature=0)
    
    summary_prompt = f"""Based on the following search results, provide a comprehensive summary that answers the research topic.
Include relevant facts, data, and insights from the sources. Make sure to reference the sources by their URLs.

Research Topic: {state["search_query"]}

Search Results:
{formatted_text}

Provide a well-organized summary with source references:"""

    response = llm.invoke(summary_prompt)
    
    return {
        "sources_gathered": sources,
        "search_query": [state["search_query"]],
        "web_research_result": [response.content],
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    
    # Get the appropriate LLM
    llm = get_llm(reasoning_model, configurable, temperature=1.0)
    structured_llm = get_structured_output(llm, Reflection, configurable)
    result = structured_llm.invoke(formatted_prompt)

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary.

    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations.

    Args:
        state: Current graph state containing the running summary and sources gathered

    Returns:
        Dictionary with state update, including running_summary key containing the formatted final summary with sources
    """
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # Get the appropriate LLM
    llm = get_llm(reasoning_model, configurable, temperature=0)
    result = llm.invoke(formatted_prompt)

    # Replace the short urls with the original urls and add all used urls to the sources_gathered
    unique_sources = []
    result_content = result.content
    for source in state["sources_gathered"]:
        if source["short_url"] in result_content:
            result_content = result_content.replace(
                source["short_url"], source["value"]
            )
            unique_sources.append(source)

    return {
        "messages": [AIMessage(content=result_content)],
        "sources_gathered": unique_sources,
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# Set the entrypoint as `generate_query`
# This means that this node is the first one called
builder.add_edge(START, "generate_query")
# Add conditional edge to continue with search queries in a parallel branch
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
# Reflect on the web research
builder.add_edge("web_research", "reflection")
# Evaluate the research
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
# Finalize the answer
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
