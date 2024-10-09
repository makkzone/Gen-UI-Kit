# Standard library imports
import os
import io
import json
import platform
import subprocess
from pathlib import Path
import shutil
from shutil import copytree
import tempfile

# Third-party imports
from typing import List, TypedDict, Annotated
from pydantic import BaseModel, Field
from langchain.output_parsers import JsonOutputToolsParser
from git import Repo

# Local library imports
from .tools import AppScreens, UiCode, ReadMeContent
from .prompts import (
    PROMPT_ADVANCED_REQUIREMENTS,
    PROMPT_GET_INITIAL_PROJECT_CONFIG,
    PROMPT_REALTIME_USER_INTERACTION_TO_GENERATE_CODE,
    PROMPT_STRUCTURED_OUTPUT,
    PROMPT_STRUCTURED_VIEWS_CODE,
    PROMPT_GENERATE_README
)
from .utils import monitor_port


# Get the current working directory
current_directory = os.getcwd()

# Define the path for the output projects directory
projects_path = os.path.join(current_directory, "output-projects")

# Create the output projects directory if it doesn't already exist
if not os.path.exists(projects_path):
    os.makedirs(projects_path, exist_ok=True)

# Initialize the JSON output parser
parser = JsonOutputToolsParser()

def download_github_folder(destination_folder):
    """
    Downloads the contents of a specific folder from a GitHub repository to a local folder.
    
    :param repo_owner: GitHub username or organization name
    :param repo_name: Name of the GitHub repository
    :param folder_path: Path of the folder in the repo to download (relative path)
    :param destination_folder: Local folder where the downloaded files will be stored
    """
    # Create the API URL for the specific folder
    repo_url = f"https://github.com/makkzone/Gen-UI-Kit-Templates.git"
    try:
        # Check if the directory already exists
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        # Clone the repo
        Repo.clone_from(repo_url, destination_folder)
        print("Repository successfully cloned.")
    except Exception as e:
        print(f"An error occurred: {e}")



def delete_temp_folder(temp_folder):
    """
    Deletes a temporary folder and its contents.
    
    :param temp_folder: Path to the temporary folder to delete
    """
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
        print(f"Temporary folder {temp_folder} deleted.")

def copy_files(src, dst):
    """
    Recursively copies files and directories from source to destination, 
    excluding 'node_modules' and 'package-lock.json'.

    Parameters:
    src (str): Source directory path.
    dst (str): Destination directory path.
    """
    
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)

        # Exclude 'node_modules' directory and 'package-lock.json' file
        if item in ["node_modules", "package-lock.json"]:
            continue

        if os.path.isdir(src_path):
            # Ensure the destination directory exists
            os.makedirs(dst_path, exist_ok=True)

            # Recursively copy contents of the directory
            copy_files(src_path, dst_path)
        else:
            # Copy individual file, preserving metadata
            shutil.copy2(src_path, dst_path)

def create_navigation(app_screen_details, navigation_json):
    """
    Generates navigation data from app screen details and writes it to a JSON file.

    Parameters:
    app_screen_details (list): List of app screen details containing view and sidebar information.
    navigation_json (str): Path to the output JSON file where the navigation data will be saved.
    """
    navigation_utilities = []

    for screen in app_screen_details:
        if screen.get('shouldRequireSidebarmenu'):
            items = [
                {
                    "id": item['viewName'].replace(' ', '').lower(),
                    "text": item['viewName'],
                    "href": item['routePath'],
                    "iconName": item['iconName']
                } 
                for item in screen['sideBarMenu']
            ]
            
            navigation_utilities.append({
                "type": "button",
                "text": screen['viewName'],
                "iconName": screen['iconName'],
                "href": f"/#{screen['routePath']}",
                "items": items
            })
        else:
            navigation_utilities.append({
                "type": "button",
                "text": screen['viewName'],
                "href": f"/#{screen['routePath']}",
                "iconName": screen['iconName']
            })

    top_navigation = {
        "HOME_TOP_NAVIGATION_UTILITIES": navigation_utilities
    }

    with open(navigation_json, "w") as file:
        # Serialize and write the navigation data to the JSON file
        json.dump(top_navigation, file, indent=4)

def kebab_to_title(kebab_string: str) -> str:
    """
    Converts a kebab-case string to title case.

    Args:
        kebab_string (str): The input string in kebab-case format.

    Returns:
        str: The input string converted to title case.
    """
    words = kebab_string.split('-')
    capitalized_words = [word.capitalize() for word in words]
    title_case = ' '.join(capitalized_words)
    return title_case

def create_file(file_path: str, file_content: str) -> None:
    """
    Creates a file and writes the provided content to it.

    Args:
        file_path (str): The path of the file to create.
        file_content (str): The content to write into the file.
    """
    with open(file_path, "w") as file:
        file.write(file_content)


def get_completed_code_for_view(
    idea_name: str, 
    idea_description: str, 
    doc_string: str, 
    function_code: str, 
    llm
) -> tuple:
    """
    Generates and retrieves the completed UI code for a given view based on the idea, its description, and the provided function code.
    
    The process involves invoking a chain of prompts and language model interactions to gather detailed requirements and structure the response.

    Args:
        idea_name (str): The name of the software idea.
        idea_description (str): A detailed description of the software idea.
        doc_string (str): The UI screen's documentation or description.
        function_code (str): The initial UI code that needs modification or completion.
        llm: The language model used for generating and structuring the code and requirements.

    Returns:
        tuple: A tuple containing:
            - str: The finalized React UI code.
            - str: The content with the functional requirements generated from the idea and description.
    """
    # Initialize the first chain for gathering advanced requirements
    chain = PROMPT_ADVANCED_REQUIREMENTS | llm
    react_ui_code = function_code
    
    # Invoke the LLM with the provided idea and UI screen details
    response = chain.invoke({
        "idea_name": idea_name, 
        "idea_description": idea_description, 
        "ui_screen": doc_string
    })
    print(response)
    
    count = 0
    if response:
        # Bind tools for generating UI screen code
        agent_ui_screen_code_generator = llm.bind_tools([UiCode])
        chain = PROMPT_STRUCTURED_VIEWS_CODE | agent_ui_screen_code_generator | parser
        
        # Invoke the chain to structure the response and generate the completed UI code
        structured_response = chain.invoke({
            "idea_name": idea_name,
            "idea_description": idea_description,
            "requirements": response.content,
            "ui_code": function_code
        })
        
        # Retry logic to handle empty responses (up to 3 retries)
        while count < 3:
            if len(structured_response) == 0:
                print(f'Empty response. Retry {count}')
                structured_response = chain.invoke({
                    "idea_name": idea_name,
                    "idea_description": idea_description,
                    "requirements": response.content,
                    "ui_code": function_code
                })
                count += 1
            else:
                break
        
        # Parse and assign the generated code from the structured response
        if len(structured_response) > 0:
            structured_response = structured_response[0]['args']
            if 'properties' in structured_response:
                react_ui_code = structured_response['properties']['react_ui_code']
            else:
                react_ui_code = structured_response['react_ui_code']

    return react_ui_code, response.content


def create_views(
    appScreenDetails: List[dict], 
    views_folder: str, 
    idea_name: str, 
    idea_description: str, 
    llm
):
    """
    Creates view components and optional sidebar navigation for each screen defined in the app.

    For each screen in the app's navigation details, this function:
    - Creates a directory for the view.
    - Generates the view's React component with header and layout.
    - Optionally generates a sidebar navigation component if required by the screen.
    - Enhances the view's content by interacting with a language model (LLM) to retrieve completed code based on the screen description.

    Args:
        appScreenDetails (List[dict]): A list of navigation details for each view, including view names, routes, and sidebar menu configuration.
        views_folder (str): The folder path where all view components will be created.
        idea_name (str): The name of the idea the views are based on.
        idea_description (str): A detailed description of the idea to help guide code generation.
        llm: The language model to assist with code completion and structuring based on descriptions.

    """
    # Ensure the views folder exists or create it
    os.makedirs(views_folder, exist_ok=True)

    # Template for the React component views
    template_view = """
    import * as React from "react";
    import {{ Container, ContentLayout, Header }} from "@cloudscape-design/components";
    {doc_string}
    function {function_name}() {{
    
    return (
        <>
        <ContentLayout
        disableOverlap
        headerBackgroundStyle="linear-gradient(to right, #2E3192, #1BFFFF)"
        headerVariant="high-contrast"
        defaultPadding
        header={{<Header variant="h1" description="{func_desc}">{header_name}</Header>}}
        >
        </ContentLayout>
        </>
    );
    }};
    
    export default {function_name};
    """

    # Template for the React sidebar navigation components
    template_sidebar = """
    import * as React from "react";
    import SideNavigation from "@cloudscape-design/components/side-navigation";

    function {function_name}() {{
        const [activeHref, setActiveHref] = React.useState("#{active_ref}");
        return (
            <SideNavigation
                activeHref={{activeHref}}
                header={{{{ href: "#{active_ref}", text: "{header_name}" }}}}
                onFollow={{event => {{
                    if (!event.detail.external) {{
                        setActiveHref(event.detail.href);
                    }}
                }}}}
                items={{{sidebar_items}}}
            />
        );
    }}
    
    export default {function_name};
    """

    # Loop through each screen's navigation details and generate components
    for navigation in appScreenDetails:
        sidebar_items = '[\n'
        view_path = f"{views_folder}/{navigation['viewName'].replace(' ', '')}View"
        os.makedirs(view_path, exist_ok=True)

        # Handle views that require a sidebar menu
        if navigation.get('shouldRequireSidebarmenu'):
            for item in navigation['sideBarMenu']:
                sidebar_items += '{' + f"type: \"link\", text: \"{item['viewName']}\", href: \"#{item['routePath']}\" " + '},\n'
                
                # Generate the function code for each sidebar menu item
                function_code = template_view.format(
                    function_name=f"{item['viewName'].replace(' ', '')}View", 
                    doc_string=f"/**\n{item['detailedDescription']}\n*/", 
                    func_desc=item['shortDescription'], 
                    header_name=item['viewName']
                )
                create_file(f"{view_path}/{item['viewName'].replace(' ', '')}View.jsx", function_code)

            sidebar_items += '\n]'
            
            # Generate the function code for the main view and sidebar component
            function_code = template_view.format(
                function_name=f"{navigation['viewName'].replace(' ', '')}View", 
                doc_string=f"/**\n{navigation['detailedDescription']}\n*/", 
                func_desc=navigation['shortDescription'], 
                header_name=navigation['viewName']
            )
            
            sidebar_code = template_sidebar.format(
                function_name=f"{navigation['viewName'].replace(' ', '')}ViewSideBarNavigation", 
                active_ref=navigation['routePath'], 
                sidebar_items=sidebar_items, 
                header_name=navigation['viewName']
            )
            
            # Write sidebar navigation code to file
            create_file(f"{view_path}/{navigation['viewName'].replace(' ', '')}ViewSideBarNavigation.jsx", sidebar_code)
        
        else:
            # If no sidebar is required, only generate the main view component
            function_code = template_view.format(
                function_name=f"{navigation['viewName'].replace(' ', '')}View", 
                doc_string=f"/**\n{navigation['detailedDescription']}\n*/", 
                func_desc=navigation['shortDescription'], 
                header_name=navigation['viewName']
            )
        
        # Enhance the generated function code using LLM for UI code completion
        function_code, requirements_data = get_completed_code_for_view(
            idea_name, idea_description, navigation['detailedDescription'], function_code, llm
        )
        
        # Write the completed view code to file
        create_file(f"{view_path}/{navigation['viewName'].replace(' ', '')}View.jsx", function_code)

    
    
def create_routes(appScreenDetails: List[dict], routes_jsx: str):
    """
    Generates route definitions for a React application based on screen details and updates the routes file.

    For each screen in the app's navigation details, this function:
    - Creates the necessary `<Route>` entries for React Router.
    - Adds sidebar navigation if the screen requires it.
    - Imports the relevant view and sidebar components.
    - Updates the provided `routes_jsx` file by injecting new route definitions and necessary imports.

    Args:
        appScreenDetails (List[dict]): A list of navigation details for each view, including view names, routes, and sidebar menu configuration.
        routes_jsx (str): The path to the JSX file where routes are defined and imports are declared.
    """
    # Template for route entry with optional sidebar and layout
    template = """
    <Route path={{'{pathName}'}} >
        <DefaultLayout sidebarNavigation={{{sideBar}}} view={{{View}}} disableSideBar={{{disableSideBar}}} />
    </Route>
    """

    routes = []  # Holds all route definitions
    imports = []  # Holds all necessary component imports

    # Loop through each screen's navigation details
    for navigation in appScreenDetails:
        # Check if the screen requires a sidebar menu
        if navigation.get('shouldRequireSidebarmenu'):
            # Loop through each sidebar menu item and generate routes and imports
            for item in navigation['sideBarMenu']:
                imports.append(
                    f"import {item['viewName'].replace(' ','')}View from './views/{navigation['viewName'].replace(' ','')}View/{item['viewName'].replace(' ','')}View';"
                )
                routes.append(
                    template.format(
                        pathName=item['routePath'],
                        sideBar=f"<{navigation['viewName'].replace(' ','')}ViewSideBarNavigation/>",
                        View=f"<{item['viewName'].replace(' ','')}View/>",
                        disableSideBar='false'
                    )
                )
            # Import the main view and sidebar for the current navigation item
            imports.append(
                f"import {navigation['viewName'].replace(' ','')}View from './views/{navigation['viewName'].replace(' ','')}View/{navigation['viewName'].replace(' ','')}View';"
            )
            imports.append(
                f"import {navigation['viewName'].replace(' ','')}ViewSideBarNavigation from './views/{navigation['viewName'].replace(' ','')}View/{navigation['viewName'].replace(' ','')}ViewSideBarNavigation';"
            )
            # Add the route for the current navigation item
            routes.append(
                template.format(
                    pathName=navigation['routePath'],
                    sideBar=f"<{navigation['viewName'].replace(' ','')}ViewSideBarNavigation/>",
                    View=f"<{navigation['viewName'].replace(' ','')}View/>",
                    disableSideBar='false'
                )
            )
        else:
            # For views without a sidebar, generate routes and imports without a sidebar
            imports.append(
                f"import {navigation['viewName'].replace(' ','')}View from './views/{navigation['viewName'].replace(' ','')}View/{navigation['viewName'].replace(' ','')}View';"
            )
            routes.append(
                template.format(
                    pathName=navigation['routePath'],
                    sideBar='<></>',
                    View=f"<{navigation['viewName'].replace(' ','')}View/>",
                    disableSideBar='true'
                )
            )

    # Add placeholders for future routes and imports
    routes.append('{/*Add new routes*/}')
    imports.append('/*import new routes*/')

    # Read the existing routes file and replace placeholders with generated routes and imports
    with open(routes_jsx, "r") as file:
        routes_jsx_content = file.read()
        routes_jsx_content = routes_jsx_content.replace('{/*Add new routes*/}', '\n'.join(routes))
        routes_jsx_content = routes_jsx_content.replace('/*import new routes*/', '\n'.join(imports))

    # Write the updated content back to the routes file
    with open(routes_jsx, "w") as file:
        file.write(routes_jsx_content)


def update_appName(project_root_folder: str, app_name: str):
    """
    Updates the application name in the project's key files including `index.html`, `package.json`,
    and `TopNavigationComponent.jsx`.

    This function:
    - Replaces instances of 'template-project' with the provided `app_name` in various files.
    - Converts `app_name` to a lowercase format without spaces for the `package.json`.
    - Converts `app_name` to a title-case format for human-readable display in the `index.html` and `TopNavigationComponent.jsx`.

    Args:
        project_root_folder (str): The root directory of the project where the key files are located.
        app_name (str): The new name of the app to replace 'template-project'.
    """
    # Define file paths
    index_html = f'{project_root_folder}/public/index.html'
    package_json = f'{project_root_folder}/package.json'
    navigation_component = f'{project_root_folder}/src/components/TopNavigationComponent.jsx'
    
    # Process the app name
    formatted_app_name = app_name.replace(' ', '').lower()  # For package.json (without spaces, all lowercase)
    formatted_title_name = kebab_to_title(app_name)         # For human-readable components (in title case)

    # Update package.json by replacing 'template-project' with the formatted app name
    with open(package_json, "r") as file:
        package_json_content = file.read()
        package_json_content = package_json_content.replace('template-project', formatted_app_name)

    # Update index.html by replacing 'template-project' with a title-case app name
    with open(index_html, "r") as file:
        index_html_content = file.read()
        index_html_content = index_html_content.replace('template-project', formatted_title_name)

    # Update TopNavigationComponent.jsx by replacing 'template-project' with a title-case app name
    with open(navigation_component, "r") as file:
        navigation_component_content = file.read()
        navigation_component_content = navigation_component_content.replace('template-project', formatted_title_name)

    # Write the updated content back to the corresponding files
    with open(package_json, "w") as file:
        file.write(package_json_content)

    with open(index_html, "w") as file:
        file.write(index_html_content)

    with open(navigation_component, "w") as file:
        file.write(navigation_component_content)


def write_readme(read_me: str, project_name: str, idea_description: str, llm) -> None:
    """
    Generates and writes a README file for a project based on the provided project details.

    This function utilizes a language model to generate structured content for the README file,
    incorporating the project name and description. It also includes a retry mechanism
    to handle cases where the initial response is empty.

    Args:
        read_me (str): The path to the README file to be created or updated.
        project_name (str): The name of the project.
        idea_description (str): A description of the project idea.
        llm: Language model for generating README content.
    """
    # Bind tools for generating README content
    readme_content_generator = llm.bind_tools([ReadMeContent])
    chain = PROMPT_GENERATE_README | readme_content_generator | parser
    
    # Invoke the chain to generate the README content
    structured_response = chain.invoke({
        "project_name": project_name,
        "project_description": idea_description
    })
    
    # Retry logic to handle empty responses (up to 3 attempts)
    count = 0
    while count < 3:
        if len(structured_response) == 0:
            print(f'Response was empty. Attempting retry {count + 1}...')
            structured_response = chain.invoke({
                "project_name": project_name,
                "project_description": idea_description
            })
            count += 1
        else:
            break
    
    # Parse and assign the generated content from the structured response
    if len(structured_response) > 0:
        structured_response = structured_response[0]['args']
        readme_content = (
            structured_response['properties']['read_me_content']
            if 'properties' in structured_response 
            else structured_response['read_me_content']
        )
        
        # Create or update the README file with the generated content
        create_file(read_me, readme_content)


def update_template_project(appScreenDetails, project_name: str, idea_name: str, idea_description: str, llm):
    """
    Updates the project template by creating necessary configurations, views, and routes 
    based on the provided application screen details.

    This function performs the following actions:
    - Creates a navigation configuration file.
    - Generates views for the application.
    - Sets up routing for the application.
    - Updates the application name in relevant files.
    - Writes a README file for the project.

    Args:
        appScreenDetails: The details of application screens generated by the LLM.
        project_name (str): The name of the project to update.
        idea_name (str): The name of the idea associated with the project.
        idea_description (str): A brief description of the idea.
        llm: The language model instance used for generating code and configurations.
    """
    # Define project folder paths
    project_root_folder = f'{projects_path}/{project_name}'
    routes_jsx = f'{project_root_folder}/src/routes.jsx'
    views_folder = f'{project_root_folder}/src/views'
    navigation_json = f'{project_root_folder}/src/configs/navigation.json'
    read_me = f'{projects_path}/{project_name}/README.md'
    
    # Create navigation configuration
    create_navigation(appScreenDetails, navigation_json)
    
    # Generate views for the application
    create_views(appScreenDetails, views_folder, idea_name, idea_description, llm)
    
    # Set up routing for the application
    create_routes(appScreenDetails, routes_jsx)
    
    # Update the application name in relevant files
    update_appName(project_root_folder, project_name)
    
    # Write README file for the project
    write_readme(read_me, project_name, idea_description, llm)


def create_project_template(project_name: str, idea_name: str, idea_description: str, llm):
    """
    Creates a new project template and installs dependencies.

    This function performs the following steps:
    - Creates a project directory.
    - Copies template files from a predefined location.
    - Installs project dependencies using npm.
    - Uses a language model to generate the initial project configuration.
    - Updates the project with generated screen details.
    - Starts the project.

    Args:
        project_name (str): Name of the project to be created.
        idea_name (str): The name of the idea associated with the project.
        idea_description (str): Description of the project idea.
        llm: Language model instance used for generating project configurations.

    Returns:
        str: Name of the project created.
    """
    temp_dir = tempfile.mkdtemp()
    download_github_folder(temp_dir)
    
    # Create the project directory
    project_path = os.path.join(projects_path, project_name)
    os.makedirs(project_path, exist_ok=True)
    
    # Copy template files to the project directory
    copytree(os.path.join(temp_dir, 'ui-templates/cloudscape-design'), project_path, dirs_exist_ok=True)
    
    
    
    # Get initial project configuration using the language model
    chain = PROMPT_GET_INITIAL_PROJECT_CONFIG | llm
    response = chain.invoke({"idea_name": idea_name, "idea_description": idea_description})
    
    # Retry mechanism in case of empty response
    count = 0
    if response:
        agent_initial_project_generator = llm.bind_tools([AppScreens])
        chain = PROMPT_STRUCTURED_OUTPUT | agent_initial_project_generator | parser
        structured_response = chain.invoke({"text": response.content})
        print(structured_response)
        while count < 3:
            if len(structured_response) == 0:
                print(f'Empty response. Retry {count}')
                structured_response = chain.invoke({"text": response.content})
                count += 1
            else:
                break
        
        print(structured_response)
        
        if len(structured_response) > 0:
            structured_response = structured_response[0]['args']
            appScreenDetails = structured_response.get('properties', {}).get('appScreenDetails', structured_response.get('appScreenDetails'))
            update_template_project(appScreenDetails, project_name, idea_name, idea_description, llm)
    
    # Start the project using npm
    start_project(project_path)


def run_existing_project(project_name: str) -> str:
    """
    Runs an existing project by starting the development server.

    This function checks if the provided project name is valid,
    constructs the project path, and then attempts to start the
    development server for the specified project.

    Args:
        project_name (str): Name of the project to be started.

    Returns:
        str: Name of the project started, or None if no project name was provided.
    """
    try:
        if project_name:
            # Construct the path to the project
            project_path = os.path.join(projects_path, project_name)
            # Start the development server for the project
            start_project(project_path)
            return project_name
        else:
            return None
    except subprocess.CalledProcessError as e:
        # Print the error message and exit if a subprocess error occurs
        print(e)
        exit()

def start_project(project_path: str) -> None:
    """
    Starts the npm development server for a project.

    This function determines the correct npm executable based on the operating system
    and runs the npm start command to launch the development server in the specified project directory.

    Args:
        project_path (str): Path to the project directory.
    """
    npm_executable = "npm.cmd" if platform.system() == "Windows" else "npm"
    shell = True if platform.system() == "Windows" else False
    
    # Install npm dependencies
    subprocess.run([npm_executable, "install", "--force"],shell=shell, cwd=project_path)
    # Run the npm start command in the specified project directory
    subprocess.run([npm_executable, "run", "start"], shell=shell, cwd=project_path)


def generate_ui_kit(project_name: str, idea_name: str, idea_description: str, llm) -> str:
    """
    Generates a React web starter kit for a given project idea and starts the project.

    This function creates a project template, runs the existing project, and monitors
    the specified port to check if the project is running successfully.

    Args:
        project_name (str): The name of the project.
        idea_name (str): The name of the idea for the project.
        idea_description (str): A detailed description of the project idea.
        llm: Language model for generating project configurations.

    Returns:
        str: A message indicating the success of the project creation and its running status.
    """
    # Create the project template
    appScreens = create_project_template(
        project_name.strip().lower().replace(" ", "_"),
        idea_name,
        idea_description,
        llm
    )
    
    # Run the existing project
    run_existing_project(project_name=project_name)

    # Monitor the specified port
    port = 3001  # Replace with the desired port
    result = monitor_port(port)

    # Construct the success message based on the port monitoring result
    if result:
        return f"""
            The React web starter kit for the project '{project_name}' has been successfully created and is now accessible at http://localhost:{port}.
            Below are the details of the views that were generated:
            {appScreens}
            """
    else:
        return f"""
            The React web starter kit for the project '{project_name}' has been created, but it is currently not accessible at the designated port.
            Below are the details of the views that were generated:
            {appScreens}
            """


class GenUiKitLangchainTool(BaseModel):
    """Tool to create a React web starter kit."""
    
    project_name: str = Field(description="Name of the project in lowercase letters.")
    idea_name: str = Field(description="The idea for the project.")
    idea_description: str = Field(description="A detailed description of the idea.")

    def _run(self, llm) -> str:
        """
        Executes the tool to create a React web starter kit for the specified project.

        Args:
            llm: Language model for generating project configurations.

        Returns:
            str: A message indicating the success of the project creation and its running status.
        """
        # Create the project template
        appScreens = create_project_template(
            self.project_name.strip().lower().replace(" ", "_"),
            self.idea_name,
            self.idea_description,
            llm
        )
        
        # Run the existing project
        run_existing_project(project_name=self.project_name)

        # Monitor the specified port
        port = 3001  # Replace with the desired port
        result = monitor_port(port)

        # Construct the success message based on the port monitoring result
        if result:
            return f"""
                The React web starter kit for the project '{self.project_name}' has been successfully created and is now accessible at http://localhost:{port}.
                Below are the details of the views that were generated:
                {appScreens}
                """
        else:
            return f"""
                The React web starter kit for the project '{self.project_name}' has been created, but it is currently not accessible at the designated port.
                Below are the details of the views that were generated:
                {appScreens}
                """
