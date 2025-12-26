# mypy: disable - error - code = "no-untyped-def,misc"
import os
import pathlib
from fastapi import FastAPI, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.genai import Client
from dotenv import load_dotenv

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


@app.get("/api/models")
async def list_models():
    """List available Gemini models from Google API in real-time."""
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
            api_key = os.getenv("GEMINI_API_KEY")
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
            "error": result.get("error")
        }
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in list_models: {error_msg}")
        return {
            "models": fallback_models,
            "source": "fallback",
            "error": error_msg
        }


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
