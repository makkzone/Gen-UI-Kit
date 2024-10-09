from langchain_core.prompts import ChatPromptTemplate

PROMPT_GET_INITIAL_PROJECT_CONFIG = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a professional business analyst. 
            You have been provided with a web application idea and its detailed description. Your task is to suggest the possible screens that the application can include for exceptional outcomes. For each screen, provide the following information:

                - Screen view name
                - Route path
                - Icon name (choose from the following: 
                    add-plus, anchor-link, angle-down, angle-left, angle-left-double, angle-right, angle-right-double, angle-up, arrow-left, arrow-right, audio-full, 
                    audio-half, audio-off, bug, calendar, call, caret-down, caret-down-filled, caret-left-filled, caret-right-filled, caret-up, caret-up-filled, check, close, 
                    contact, copy, delete-marker, download, drag-indicator, edit, ellipsis, envelope, expand, external, file, file-open, filter, flag, folder, folder-open, 
                    gen-ai, group, group-active, heart, heart-filled, insert-row, key, keyboard, lock-private, menu, microphone, microphone-off, multiscreen, notification, 
                    redo, refresh, remove, resize-area, script, search, security, send, settings, share, shrink, star, star-filled, star-half, status-in-progress, 
                    status-info, status-negative, status-pending, status-positive, status-stopped, status-warning, subtract-minus, suggestions, thumbs-down, thumbs-down-filled, 
                    thumbs-up, thumbs-up-filled, ticket, treeview-collapse, treeview-expand, undo, unlocked, upload, upload-download, user-profile, user-profile-active, 
                    video-off, video-on, video-unavailable, view-full, view-horizontal, view-vertical, zoom-in, zoom-out, zoom-to-fit)
                - Short description of the screen
                - Detailed description of the screen
                - Does the screen have a submenu?
                - If submenu exists, provide:
                    - Submenu item name
                    - Route path for the submenu item
                    - Short description of the submenu item
                    - Detailed description of the submenu item
            """
        ),(
            "user",
            """
            Here is the software web application idea and its description.

             #Idea Name:
            <idea_name>
            {idea_name}
            </idea_name>

            #Idea Description:
            <idea_description>
            {idea_description}
            </idea_description>
            """
        )
    ]
)

PROMPT_STRUCTURED_OUTPUT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful AI assistant. 
            Your task is to take the unstructured text provided and convert it into a well-organized table format using JSON.
            """
        ),(
            "user",
            """
            Here is the text.
            <text>
            {text}
            </text>
            """
        )
    ]
)

PROMPT_ADVANCED_REQUIREMENTS = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a subject matter expert for the project {idea_name}. Below is the detailed description of the idea:

            ##Idea Description:
            <idea_description>
            {idea_description}
            </idea_description>

            You are provided with the details of one UI screen related to this idea. Your task is to identify and list all the functionalities that this particular screen should include.
            """
        ),(
            "user",
            """
            Here are the UI screen details.

            ##UI Screen Details:
            <ui_screen>
            {ui_screen}
            </ui_screen>
            """
        )
    ]
)

PROMPT_REALTIME_USER_INTERACTION_TO_GENERATE_CODE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a React.js coding assistant with expertise in Cloudscape Design UI Kit (https://cloudscape.design/components). 
            Below are the details of the project, including the idea, its description, requirements, and existing UI code.

            ## Idea:
            <idea_name>
            {idea_name}
            </idea>

            ## Idea Description:
            <idea_description>
            {idea_description}
            </idea_description>

            ## UI Screen Code that requires modification based on user request:
            <ui_code>
            {ui_code}
            </ui_code>

            Your task is to make the necessary changes to the UI code based on the user’s request.

            Here is the request from the user:
            """,
        ),
        ("user", "{user_request}"),
    ]
)

PROMPT_STRUCTURED_VIEWS_CODE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a React.js developer experienced with Cloudscape Design UI Kit (https://cloudscape.design/components). 
            Your task is to complete the given UI code using the Cloudscape Design UI Kit based on the specified requirements in context to the idea and its description. 
            Use dummy data to populate the screen if necessary.
            """
        ),(
            "user",
            """
            Below are the details, including the idea, its description, requirements, and UI code.

            ## Idea:
            <idea_name>
            {idea_name}
            </idea>

            ## Idea Description:
            <idea_description>
            {idea_description}
            </idea_description>

            ## Requirements:
            <requirements>
            {requirements}
            </requirements>

            ## UI Code:
            <ui_code>
            {ui_code}
            </ui_code>

            Please complete the UI code based on the given requirements for the idea.

            Note: Ensure the code strictly follows the provided requirements.
            """
        )
    ]
)

PROMPT_GENERATE_README = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a technical documentation expert. 
            Your task is to generate a comprehensive and professional README file for a software project based on the provided idea and its description. 
            The README should include the following sections:

            1. **Project Title**: A clear and concise name for the project.
            2. **Project Description**: A detailed overview of the project's purpose, key features, and functionality.
            3. **Installation Instructions**: A step-by-step guide on how to install this react project.

            Ensure the README is well-structured and easy to follow.
            """
        ),(
            "user",
            """
            Here is the project and its description:

            ## Project Name:
            <project_name>
            {project_name}
            </project_name>

            ## Project Description:
            <project_description>
            {project_description}
            </project_description>
            """
        )
    ]
)

