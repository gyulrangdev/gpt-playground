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
    assistant_key = os.environ.get(f"OPENAI_{name.upper().replace(" ",'_')}_ASSISTANT_KEY")
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
        {‘diagram’: ‘mermaid diagram given by assistant’, ‘explain’: ‘your explain about architecture’}
        '''
    )
    return run

# 추가 작업 처리
def handle_required_action(client, run):
    tool_outputs = []
    
    if run.required_action and run.required_action.submit_tool_outputs:
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
    
    return run

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
            "name": "System Designer",
            "instructions": (
                "You are the world's best system architecture designer. "
                "System Designer is tailored for designing architectures for applications with over 100,000 daily active users (DAU). "
                "It provides system designs that include distributed processing, caching, message queues, CDN, separated service workers for key functionalities, "
                "and integrated backup and logging systems. Each response includes a vertical Mermaid diagram, with all contents written in Korean, "
                "to visually represent the complete and scalable system architecture."
                "The information from your answer would be returned as a JSON object : diagram, explain"
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
                                "diagram": {
                                    "type": "string",
                                    "description": "Print mermaid diagram from your answer."
                                },
                                "explain": {
                                    "type": "string",
                                    "description": "Explain about diagram and overall architecture."
                                }
                            },
                            "required": ["diagram", "explain"]
                        }
                    }
                }
            ]
        },
        {
            "name": "AWS Infrastructure",
            "instructions": (
                "You are an expert in setting up AWS infrastructure. "
                "AWS Infrastructure assistant helps in creating scalable and robust cloud infrastructure using AWS services."
                "The response includes detailed architecture setup instructions with Terraform scripts, cost estimates, and scaling strategies."
            ),
            "tools": []
        },
        {
            "name": "Diagram Generator",
            "instructions": (
                "You are a skilled diagram generator. "
                "Diagram Generator assistant provides detailed, professional diagrams for system architectures."
                "Each response includes a clear, precise, and visually appealing diagram representing the system architecture."
            ),
            "tools": []
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

    # 시스템 디자인 어시스턴트 실행
    system_design_run = create_and_run_message(
        client,
        thread_key,
        assistant_keys["System Designer"],
        "유튜브 릴스 기능을 추가하기 위한 전체 아키텍처를 설계해줘. AWS를 이용해서 만들거야."
    )
    
    while system_design_run.status == 'requires_action':
        system_design_run = handle_required_action(client, system_design_run)

    print_run_status(system_design_run)
    
    # AWS 인프라 어시스턴트 실행
    if system_design_run.status == 'completed':
        aws_infra_run = create_and_run_message(
            client,
            thread_key,
            assistant_keys["AWS Infrastructure"],
            "위의 아키텍처에 맞는 AWS 인프라를 설정해줘."
        )
        
        while aws_infra_run.status == 'requires_action':
            aws_infra_run = handle_required_action(client, aws_infra_run)

        print_run_status(aws_infra_run)
    
        # 다이어그램 생성 어시스턴트 실행
        if aws_infra_run.status == 'completed':
            diagram_generator_run = create_and_run_message(
                client,
                thread_key,
                assistant_keys["Diagram Generator"],
                "위의 아키텍처를 기반으로 다이어그램을 만들어줘."
            )
            
            while diagram_generator_run.status == 'requires_action':
                diagram_generator_run = handle_required_action(client, diagram_generator_run)

            print_run_status(diagram_generator_run)
