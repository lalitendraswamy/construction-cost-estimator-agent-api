from langchain_core.prompts import ChatPromptTemplate

LANGUAGE_DETECT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Identify the language of the user's message. Users may write Telugu or Hindi in "
            "Latin letters (e.g. 'naku illu kattali' is Telugu, 'mujhe ghar banana hai' is "
            "Hindi). Set confident=false for very short or language-neutral text such as "
            "numbers, 'ok', 'G+1, standard'.",
        ),
        ("human", "{text}"),
    ]
)
