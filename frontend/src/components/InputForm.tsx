import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { SquarePen, Brain, Send, StopCircle, Zap, Cpu } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Updated InputFormProps
interface InputFormProps {
  onSubmit: (inputValue: string, effort: string, model: string) => void;
  onCancel: () => void;
  isLoading: boolean;
  hasHistory: boolean;
}

interface GeminiModel {
  name: string;
  display_name: string;
  description: string;
}

export const InputForm: React.FC<InputFormProps> = ({
  onSubmit,
  onCancel,
  isLoading,
  hasHistory,
}) => {
  const [internalInputValue, setInternalInputValue] = useState("");
  const [effort, setEffort] = useState("medium");
  const [model, setModel] = useState("models/gemini-2.5-flash");
  const [availableModels, setAvailableModels] = useState<GeminiModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);

  // Fetch available models from backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const apiUrl = import.meta.env.DEV
          ? "http://localhost:2024"
          : "http://localhost:8123";
        console.log("Fetching models from:", `${apiUrl}/api/models`);
        const response = await fetch(`${apiUrl}/api/models`);
        if (response.ok) {
          const data = await response.json();
          console.log("Models fetched successfully:", data.models.length, "models, source:", data.source);
          setAvailableModels(data.models || []);
        } else {
          console.error("Failed to fetch models:", response.statusText);
          // Fallback to default models
          setAvailableModels([
            { name: "models/gemini-2.5-flash", display_name: "Gemini 2.5 Flash", description: "" },
            { name: "models/gemini-2.5-pro", display_name: "Gemini 2.5 Pro", description: "" },
          ]);
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        // Fallback to default models
        setAvailableModels([
          { name: "models/gemini-1.5-flash", display_name: "Gemini 1.5 Flash", description: "" },
          { name: "models/gemini-1.5-pro", display_name: "Gemini 1.5 Pro", description: "" },
        ]);
      } finally {
        setModelsLoading(false);
        console.log("Models loading complete");
      }
    };

    fetchModels();
  }, []);

  const handleInternalSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    console.log("Submit clicked, input:", internalInputValue, "effort:", effort, "model:", model);
    if (!internalInputValue.trim()) {
      console.log("Input is empty, not submitting");
      return;
    }
    console.log("Calling onSubmit...");
    onSubmit(internalInputValue, effort, model);
    setInternalInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit with Ctrl+Enter (Windows/Linux) or Cmd+Enter (Mac)
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleInternalSubmit();
    }
  };

  const isSubmitDisabled = !internalInputValue.trim() || isLoading;

  return (
    <form
      onSubmit={handleInternalSubmit}
      className={`flex flex-col gap-2 p-3 pb-4`}
    >
      <div
        className={`flex flex-row items-center justify-between text-white rounded-3xl rounded-bl-sm ${
          hasHistory ? "rounded-br-sm" : ""
        } break-words min-h-7 bg-neutral-700 px-4 pt-3 `}
      >
        <Textarea
          value={internalInputValue}
          onChange={(e) => setInternalInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Who won the Euro 2024 and scored the most goals?"
          className={`w-full text-neutral-100 placeholder-neutral-500 resize-none border-0 focus:outline-none focus:ring-0 outline-none focus-visible:ring-0 shadow-none
                        md:text-base  min-h-[56px] max-h-[200px]`}
          rows={1}
        />
        <div className="-mt-3">
          {isLoading ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-red-500 hover:text-red-400 hover:bg-red-500/10 p-2 cursor-pointer rounded-full transition-all duration-200"
              onClick={onCancel}
            >
              <StopCircle className="h-5 w-5" />
            </Button>
          ) : (
            <Button
              type="submit"
              variant="ghost"
              className={`${
                isSubmitDisabled
                  ? "text-neutral-500"
                  : "text-blue-500 hover:text-blue-400 hover:bg-blue-500/10"
              } p-2 cursor-pointer rounded-full transition-all duration-200 text-base`}
              disabled={isSubmitDisabled}
            >
              Search
              <Send className="h-5 w-5" />
            </Button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex flex-row gap-2">
          <div className="flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 focus:ring-neutral-500 rounded-xl rounded-t-sm pl-2  max-w-[100%] sm:max-w-[90%]">
            <div className="flex flex-row items-center text-sm">
              <Brain className="h-4 w-4 mr-2" />
              Effort
            </div>
            <Select value={effort} onValueChange={setEffort}>
              <SelectTrigger className="w-[120px] bg-transparent border-none cursor-pointer">
                <SelectValue placeholder="Effort" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                <SelectItem
                  value="low"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  Low
                </SelectItem>
                <SelectItem
                  value="medium"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  Medium
                </SelectItem>
                <SelectItem
                  value="high"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  High
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 focus:ring-neutral-500 rounded-xl rounded-t-sm pl-2  max-w-[100%] sm:max-w-[90%]">
            <div className="flex flex-row items-center text-sm ml-2">
              <Cpu className="h-4 w-4 mr-2" />
              Model
            </div>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="w-[200px] bg-transparent border-none cursor-pointer">
                <SelectValue placeholder={modelsLoading ? "Loading..." : "Select Model"} />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer max-h-[300px]">
                {modelsLoading ? (
                  <SelectItem value="loading" disabled>
                    Loading models...
                  </SelectItem>
                ) : availableModels.length === 0 ? (
                  <SelectItem value="none" disabled>
                    No models available
                  </SelectItem>
                ) : (
                  availableModels.map((m) => (
                    <SelectItem
                      key={m.name}
                      value={m.name}
                      className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                    >
                      <div className="flex items-center">
                        {m.name.includes("flash") ? (
                          <Zap className="h-4 w-4 mr-2 text-yellow-400" />
                        ) : (
                          <Cpu className="h-4 w-4 mr-2 text-purple-400" />
                        )}
                        <span className="truncate max-w-[200px]" title={m.display_name}>
                          {m.display_name.replace("models/", "")}
                        </span>
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
        </div>
        {hasHistory && (
          <Button
            className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer rounded-xl rounded-t-sm pl-2 "
            variant="default"
            onClick={() => window.location.reload()}
          >
            <SquarePen size={16} />
            New Search
          </Button>
        )}
      </div>
    </form>
  );
};
