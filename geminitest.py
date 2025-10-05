import google.generativeai as genai
import config

genai.configure(api_key=config.apikey)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config=generation_config,
    safety_settings=safety_settings
)

print("Gemini model initialized successfully")


def get_ai_response_with_context(query, history=[]):
    """
    Get AI response with conversation context
    
    Args:
        query (str): Current user question
        history (list): Previous conversation [{'role': 'user/assistant', 'content': '...'}]
        
    Returns:
        str: AI's response
    """
    if not query or not query.strip():
        return "Please ask me something!"
    
    try:
        # Build context from history
        context = "You are Friday, a helpful AI assistant like JARVIS from Iron Man. Be friendly, concise, and helpful.\n\n"
        
        if history and len(history) > 0:
            context += "Previous conversation:\n"
            for msg in history[-10:]:  # Last 10 messages
                role = "User" if msg['role'] == 'user' else "Friday"
                context += f"{role}: {msg['content']}\n"
            context += "\n"
        
        context += f"Current question: {query}\n\nProvide a helpful response:"
        
        response = model.generate_content(context)
        
        if not response.text:
            return "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        return response.text.strip()
        
    except Exception as e:
        error_msg = str(e)
        print(f"AI Error: {error_msg}")
        
        if "quota" in error_msg.lower():
            return "I've reached my API quota limit. Please try again later."
        elif "api key" in error_msg.lower() or "invalid" in error_msg.lower():
            return "There's an issue with my API key. Please check the configuration."
        elif "404" in error_msg or "not found" in error_msg.lower():
            return "The AI model is not available. Please check the model name."
        else:
            return f"Sorry, I'm having trouble: {error_msg}"


# Keep old function for backward compatibility
def get_ai_response(query):
    return get_ai_response_with_context(query, [])