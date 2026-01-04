# mypy: disable - error - code = "no-untyped-def,misc"
import os
import pathlib
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from agent.configuration import get_active_provider, get_provider_config

load_dotenv()

# Define the FastAPI app
app = FastAPI()

# Add CORS middleware to allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8123"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


@app.get("/api/provider")
async def get_provider_info():
    """Get information about the active provider."""
    provider = get_active_provider()
    provider_config = get_provider_config()
    
    return {
        "active_provider": provider,
        "has_api_key": bool(provider_config.get("api_key") or provider_config.get("exa_api_key")),
    }


@app.get("/api/models")
async def list_models():
    """List available models based on the active provider."""
    import asyncio
    
    provider = get_active_provider()
    provider_config = get_provider_config()
    
    if provider == "google":
        return await _list_google_models(provider_config)
    elif provider == "openrouter":
        return await _list_openrouter_models(provider_config)
    elif provider == "local":
        return await _list_local_models(provider_config)
    else:
        return {"models": [], "source": "unknown", "error": f"Unknown provider: {provider}"}


async def _list_google_models(provider_config: dict):
    """List available Google Gemini models."""
    import asyncio
    
    # Fallback models in case API call fails
    fallback_models = [
        {
            "name": "models/gemini-2.5-flash",
            "display_name": "Gemini 2.5 Flash",
            "description": "Fast and efficient model for most tasks"
        },
        {
            "name": "models/gemini-2.5-pro",
            "display_name": "Gemini 2.5 Pro",
            "description": "Most capable model for complex tasks"
        },
        {
            "name": "models/gemini-2.0-flash",
            "display_name": "Gemini 2.0 Flash",
            "description": "Fast experimental model"
        },
        {
            "name": "models/gemini-2.0-flash-exp",
            "display_name": "Gemini 2.0 Flash (Experimental)",
            "description": "Latest experimental flash model"
        },
    ]
    
    def _fetch_models_from_google():
        """Fetch models from Google API (runs in thread pool)."""
        try:
            from google.genai import Client
            
            api_key = provider_config.get("api_key") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("WARN: GEMINI_API_KEY not set, using fallback models")
                return {"models": fallback_models, "fetched": False, "error": "No API key"}
            
            client = Client(api_key=api_key)
            models = []
            
            print("INFO: Attempting to fetch models from Google API...")
            
            # List all models from Google API
            model_count = 0
            excluded_keywords = ['embedding', 'tts', 'image', 'robotics', 'computer-use']
            
            for model in client.models.list():
                model_count += 1
                
                # Try different ways to filter models
                should_include = False
                model_name_lower = model.name.lower()
                
                # Method 1: Check supported_generation_methods
                if hasattr(model, 'supported_generation_methods'):
                    if 'generateContent' in model.supported_generation_methods:
                        should_include = True
                
                # Method 2: Check if it's a text generation gemini model by name
                if not should_include and 'gemini' in model_name_lower:
                    # Exclude models with certain keywords
                    if not any(keyword in model_name_lower for keyword in excluded_keywords):
                        should_include = True
                    
                if should_include:
                    # Extract display name
                    display_name = model.display_name if hasattr(model, 'display_name') else model.name
                    # Clean up the display name
                    if display_name.startswith("models/"):
                        display_name = display_name.replace("models/", "").replace("-", " ").title()
                    
                    # Get description
                    description = ""
                    if hasattr(model, 'description'):
                        description = model.description
                    
                    models.append({
                        "name": model.name,
                        "display_name": display_name,
                        "description": description,
                    })
                    print(f"  ✓ Found model: {model.name}")
            
            print(f"INFO: Fetched {len(models)} models (out of {model_count} total)")
            
            # If we got models from API, return them; otherwise use fallback
            if models:
                return {"models": models, "fetched": True, "error": None}
            else:
                print("WARN: No models found in API response, using fallback")
                return {"models": fallback_models, "fetched": False, "error": "No models in response"}
            
        except Exception as e:
            error_msg = str(e)
            print(f"WARN: Failed to fetch models from Google API: {error_msg}")
            print("Using fallback model list")
            return {"models": fallback_models, "fetched": False, "error": error_msg}
    
    # Run blocking call in a thread pool to avoid blocking the event loop
    try:
        result = await asyncio.to_thread(_fetch_models_from_google)
        return {
            "models": result["models"],
            "source": "google_api" if result["fetched"] else "fallback",
            "provider": "google",
            "error": result.get("error")
        }
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in list_models: {error_msg}")
        return {
            "models": fallback_models,
            "source": "fallback",
            "provider": "google",
            "error": error_msg
        }


async def _list_openrouter_models(provider_config: dict):
    """List available OpenRouter models."""
    import asyncio
    import httpx
    
    # Fallback models for OpenRouter
    fallback_models = [
        {
            "name": "anthropic/claude-3.5-sonnet",
            "display_name": "Claude 3.5 Sonnet",
            "description": "Anthropic's most capable model"
        },
        {
            "name": "anthropic/claude-3-haiku",
            "display_name": "Claude 3 Haiku",
            "description": "Fast and efficient Claude model"
        },
        {
            "name": "openai/gpt-4o",
            "display_name": "GPT-4o",
            "description": "OpenAI's flagship model"
        },
        {
            "name": "openai/gpt-4o-mini",
            "display_name": "GPT-4o Mini",
            "description": "Fast and affordable GPT-4 variant"
        },
        {
            "name": "google/gemini-pro-1.5",
            "display_name": "Gemini Pro 1.5",
            "description": "Google's advanced Gemini model"
        },
        {
            "name": "meta-llama/llama-3.1-70b-instruct",
            "display_name": "Llama 3.1 70B",
            "description": "Meta's open-source large model"
        },
    ]
    
    async def _fetch_models():
        try:
            api_key = provider_config.get("api_key", "")
            if not api_key:
                return {"models": fallback_models, "fetched": False, "error": "No API key"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                
                if response.status_code != 200:
                    return {"models": fallback_models, "fetched": False, "error": f"API error: {response.status_code}"}
                
                data = response.json()
                models = []
                
                for model in data.get("data", []):
                    # Filter for text generation models
                    model_id = model.get("id", "")
                    
                    # Skip embedding models and other non-chat models
                    if "embed" in model_id.lower() or "vision" in model_id.lower():
                        continue
                    
                    models.append({
                        "name": model_id,
                        "display_name": model.get("name", model_id),
                        "description": model.get("description", ""),
                    })
                
                if models:
                    return {"models": models[:50], "fetched": True, "error": None}  # Limit to 50 models
                else:
                    return {"models": fallback_models, "fetched": False, "error": "No models found"}
                
        except Exception as e:
            return {"models": fallback_models, "fetched": False, "error": str(e)}
    
    try:
        result = await _fetch_models()
        return {
            "models": result["models"],
            "source": "openrouter_api" if result["fetched"] else "fallback",
            "provider": "openrouter",
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "models": fallback_models,
            "source": "fallback",
            "provider": "openrouter",
            "error": str(e)
        }


async def _list_local_models(provider_config: dict):
    """List models available on local llama-server."""
    import asyncio
    import httpx
    
    # Default model for local llama-server
    default_models = [
        {
            "name": "gpt-3.5-turbo",
            "display_name": "Local Model",
            "description": "Currently loaded model on llama-server"
        },
    ]
    
    async def _fetch_models():
        try:
            base_url = provider_config.get("base_url", "http://localhost:8080/v1")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/models",
                    timeout=5.0,
                )
                
                if response.status_code != 200:
                    return {"models": default_models, "fetched": False, "error": f"API error: {response.status_code}"}
                
                data = response.json()
                models = []
                
                for model in data.get("data", []):
                    models.append({
                        "name": model.get("id", "gpt-3.5-turbo"),
                        "display_name": model.get("id", "Local Model"),
                        "description": "Locally running model",
                    })
                
                if models:
                    return {"models": models, "fetched": True, "error": None}
                else:
                    return {"models": default_models, "fetched": False, "error": "No models found"}
                
        except Exception as e:
            return {"models": default_models, "fetched": False, "error": str(e)}
    
    try:
        result = await _fetch_models()
        return {
            "models": result["models"],
            "source": "local_api" if result["fetched"] else "fallback",
            "provider": "local",
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "models": default_models,
            "source": "fallback",
            "provider": "local",
            "error": str(e)
        }


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
