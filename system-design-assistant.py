from openai import OpenAI
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
api_key = os.environ.get("OPENAI_API_KEY", "<your OpenAI API key if not set as env var>")
if not api_key:
    raise ValueError("API key is missing. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

# 어시스턴트 ID 로드 또는 생성
assistant_key = os.environ.get("OPENAI_ASSISTANT_KEY")
if not assistant_key:
    assistant = client.beta.assistants.create(
        name="System Designer",
        instructions=(
            "You are the world's best system architecture designer. "
            "System Designer is tailored for designing architectures for applications with over 100,000 daily active users (DAU). "
            "It provides system designs that include distributed processing, caching, message queues, CDN, separated service workers for key functionalities, "
            "and integrated backup and logging systems. Each response includes a vertical Mermaid diagram, with all contents written in Korean, "
            "to visually represent the complete and scalable system architecture."
        ),
        tools=[{"type": "code_interpreter"}],
        model="gpt-3.5-turbo"
    )
    assistant_key = assistant.id
    print(f"New assistant created with ID: {assistant_key}")
else:
    print(f"Using existing assistant with ID: {assistant_key}")

# 스레드 ID 로드 또는 생성
thread_key = os.environ.get("OPENAI_THREAD_KEY")
if not thread_key:
    thread = client.beta.threads.create()
    thread_key = thread.id
    print(f"New thread created with ID: {thread_key}")
else:
    print(f"Using existing thread with ID: {thread_key}")

# 메시지 추가
message_content = "e북 시스템을 위한 아키텍처를 설계해줘."
message = client.beta.threads.messages.create(
    thread_id=thread_key,
    role="user",
    content=message_content
)

# 어시스턴트 실행
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread_key,
    assistant_id=assistant_key,
    instructions="한국어로 답변해. 간단한 아키텍쳐를 mermaid diagram으로 그려줘."
)

# 실행 결과 출력
if run.status == 'completed':
    messages = client.beta.threads.messages.list(thread_id=thread_key)
    for message in messages.data:
        print(message.content[0].text.value)
        print('-------')
else:
    print(f"Run status: {run.status}")
