from openai import OpenAI
import os
from dotenv import load_dotenv

# 환경 변수 로드 및 OpenAI 클라이언트 초기화
def initialize_openai_client():
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY", "<your OpenAI API key if not set as env var>")
    if not api_key:
        raise ValueError("API key is missing. Please set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)

# 어시스턴트 생성 또는 로드
def get_or_create_assistant(client, name, instructions, tools, model="gpt-3.5-turbo"):
    assistant_key = os.environ.get(f"OPENAI_{name.upper().replace(' ', '_')}_KEY")
    if not assistant_key:
        assistant = client.beta.assistants.create(
            name=name,
            instructions=instructions,
            response_format={"type": "json_object"},
            tools=tools,
            model=model
        )
        assistant_key = assistant.id
        print(f"New assistant created with ID: {assistant_key}")
    else:
        print(f"Using existing assistant with ID: {assistant_key}")
    return assistant_key

# 스레드 생성 또는 로드
def get_or_create_thread(client):
    thread_key = os.environ.get("OPENAI_THREAD_KEY")
    if not thread_key:
        thread = client.beta.threads.create()
        thread_key = thread.id
        print(f"New thread created with ID: {thread_key}")
    else:
        print(f"Using existing thread with ID: {thread_key}")
    return thread_key

# 메시지 생성 및 실행
def create_and_run_message(client, thread_key, assistant_key, message_content):
    message = client.beta.threads.messages.create(
        thread_id=thread_key,
        role="user",
        content=message_content
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_key,
        assistant_id=assistant_key,
        instructions='''
        please output the information in structured JSON format without using markdown code blocks.
        make response like this.
        {'requirements' : 'your system analysis of the requirements',
        ‘diagram’: ‘mermaid diagram given by assistant’,
        ‘explain’: ‘your explain about architecture’}
        '''
    )
    return run

# 추가 작업 처리
def handle_required_action(client, run):
    tool_outputs = []
    
    if run.required_action and hasattr(run.required_action, 'submit_tool_outputs') and run.required_action.submit_tool_outputs:
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "system_design":
                arguments = tool.function.arguments
                print(f"Function arguments: {arguments}")  # 여기서 arguments를 출력합니다
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": arguments
                })

        if tool_outputs:
            try:
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=run.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)
        else:
            print("No tool outputs to submit.")
    
    return run, tool_outputs

# 실행 결과 추출
def extract_result_from_run(run):
    tool_outputs = []
    tool_arguments = {}
    
    if run.required_action and hasattr(run.required_action, 'submit_tool_outputs') and run.required_action.submit_tool_outputs:
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            print("tool :: " , tool)
            if tool.function.name == "system_design":
                tool_arguments = tool.function.arguments
                print(f"Function arguments: {tool_arguments}")  # 여기서 arguments를 출력합니다
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": tool_arguments
                })
                print("tool_outputs :: " , tool_outputs)
    return tool_outputs

# 실행 결과 출력
def print_run_status(run):
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=run.thread_id
        )
        for message in messages.data:
            print(message)
            print('-------')
    else:
        print(f"Run status: {run.status}")

# 메인 실행 흐름
if __name__ == "__main__":
    client = initialize_openai_client()

    # 어시스턴트 정의
    assistants = [
        {
            "name": "Requirements Analysis Agent",
            "instructions": (
                "You are an expert in analyzing requirements for large-scale applications."
                "Your task is to gather and analyze the requirements needed to add new features to an existing application."
                "Each response should include a clear and detailed requirements document in JSON format."
            ),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "system_design",
                        "description": "It provides analysis of the requirements needed to add new features to an existing application",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "requirements": {
                                    "type": "string",
                                    "description": "List up about analysis of the requirements."
                                }
                            },
                            "required": ["requirements"]
                        }
                    }
                }
            ]
        },
        {
            "name": "System Architecture Design Agent",
            "instructions": (
                "You are the world's best system architecture designer. "
                "System Architecture Design Agent is tailored for designing AWS infra architectures for applications with over 100,000 daily active users (DAU). "
                "It provides system designs that include distributed processing, caching, message queues, CDN, separated service workers for key functionalities, "
                "and integrated backup and logging systems. Each response includes a vertical Mermaid diagram, with all contents written in Korean, "
                "to visually represent the complete and scalable system architecture."
                "The information from your answer would be returned as a JSON object : explain"
            ),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "system_design",
                        "description": "It provides system designs that include distributed processing, caching, message queues, CDN, separated service workers for key functionalities",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "explain": {
                                    "type": "string",
                                    "description": "Explain about diagram and overall architecture."
                                }
                            },
                            "required": ["explain"]
                        }
                    }
                }
            ]
        },
        {
            "name": "Diagram Generation Agent",
            "instructions": (
                "You are a skilled mermaid diagram generator. "
                "Diagram Generation Agent provides detailed, professional diagrams for system architectures."
                "Each response includes a clear, precise, and visually appealing diagram representing the system architecture."
                "The information from your answer would be returned as a JSON object : diagram"
            ),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "system_design",
                        "description": "It provides mermaid diagram from infra architecture explanation",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "diagram": {
                                    "type": "string",
                                    "description": "Mermaid diagram from your answer."
                                }
                            },
                            "required": ["diagram"]
                        }
                    }
                }
            ]
        }
    ]

    assistant_keys = {}
    for assistant in assistants:
        assistant_keys[assistant["name"]] = get_or_create_assistant(
            client,
            assistant["name"],
            assistant["instructions"],
            assistant["tools"]
        )

    thread_key = get_or_create_thread(client)

    # 요구사항 분석 에이전트 실행
    requirements_run = create_and_run_message(
        client,
        thread_key,
        assistant_keys["Requirements Analysis Agent"],
        "유튜브 릴스 기능을 추가하기 위한 요구사항을 분석해줘."
    )
    
    while requirements_run.status == 'requires_action':
        requirements_run, requirements_result = handle_required_action(client, requirements_run)
    
    print(requirements_result)

    # requirements_result = extract_result_from_run(requirements_run)

    # 시스템 아키텍처 설계 에이전트 실행
    if requirements_result:
        system_design_run = create_and_run_message(
            client,
            thread_key,
            assistant_keys["System Architecture Design Agent"],
            f"유튜브 릴스 기능을 추가하기 위한 AWS 인프라 아키텍처를 설계해줘. 요구사항은 다음과 같아: {requirements_result}"
        )
        
        while system_design_run.status == 'requires_action':
            system_design_run, system_design_result = handle_required_action(client, system_design_run)

        print(system_design_result)
        # 다이어그램 생성 에이전트 실행
        if system_design_result:
            diagram_generator_run = create_and_run_message(
                client,
                thread_key,
                assistant_keys["Diagram Generation Agent"],
                f"위의 아키텍처를 기반으로 다이어그램을 만들어줘. 아키텍처 설명은 다음과 같아: {system_design_result}"
            )

            while diagram_generator_run.status == 'requires_action':
                diagram_generator_run, diagram_generator_result = handle_required_action(client, diagram_generator_run)

            diagram_generator_result = extract_result_from_run(diagram_generator_run)