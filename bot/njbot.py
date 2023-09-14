import atexit
from dotenv import load_dotenv
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering import QuestionAnsweringClient
from azure.ai.language.conversations import ConversationAnalysisClient
from azure.search.documents import SearchClient

from dto.message_request import MessageRequest

# Endpoint, Key 가져오기
load_dotenv()

ls_endpoint = os.environ.get('LS_ENDPOINT')
ls_credential = AzureKeyCredential(os.environ.get('LS_CREDENTIAL_KEY'))

cs_endpoint = os.environ.get('CS_ENDPOINT')
cs_credential = AzureKeyCredential(os.environ.get('CS_CREDENTIAL_KEY'))
cs_board_index_name = os.environ.get('CS_BOARD_INDEX_NAME')
cs_location_index_name = os.environ.get('CS_LOCATION_INDEX_NAME')

qa_project = os.environ.get('QA_PROJECT')
qa_deployment = os.environ.get('QA_DEPLOYMENT')

clu_project = os.environ.get('CLU_PROJECT')
clu_deployment = os.environ.get('CLU_DEPLOYMENT')


class NJBot:
    # Azure 서비스 객체 할당
    def __init__(self):
        self.clu_client = ConversationAnalysisClient(os.environ.get('LS_ENDPOINT'), ls_credential)
        self.qna_client = QuestionAnsweringClient(ls_endpoint, ls_credential)
        self.search_board_client = SearchClient(endpoint=cs_endpoint,
                                                index_name=cs_board_index_name,
                                                credential=cs_credential,
                                                api_version='2021-04-30-Preview')
        self.search_location_client = SearchClient(endpoint=cs_endpoint,
                                                   index_name=cs_location_index_name,
                                                   credential=cs_credential,
                                                   api_version='2021-04-30-Preview')

        atexit.register(self.__cleanup)

    # 의도 판별
    async def __clu(self, message):
        result = self.clu_client.analyze_conversation(
            task={
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "text": message
                    },
                },
                "parameters": {
                    "projectName": clu_project,
                    "deploymentName": clu_deployment
                }
            }
        )

        intent = result['result']['prediction']['topIntent']

        if intent == 'Location':
            entities = result['result']['prediction']['entities']

            if len(entities) == 0:
                return {'intent': 'None'}

            place = ''

            for ent in entities:
                place = place + ent['text'] + ' '

            return {'intent': intent, 'place': place}

        return {'intent': intent}

    # QnA 서비스
    async def __qna(self, message):
        result = self.qna_client.get_answers(question=message,
                                             project_name=qa_project,
                                             deployment_name=qa_deployment)

        answer = result.answers[0].answer
        if result.answers[0].confidence < 0.5:
            return '죄송합니다. 무슨 말씀이신지 잘 모르겠어요.'
        print(result.answers[0].confidence)

        return answer

    # 응답 메시지 생성
    async def response(self, mr: MessageRequest):
        user_message = mr.message

        clu_result = await self.__clu(user_message)

        # 의도에 따른 답변 생성
        if clu_result['intent'] == 'None':
            return {'message': await self.__qna(user_message)}
        elif clu_result['intent'] == 'Location':
            results = self.search_location_client.search(search_text=clu_result['place'],
                                                         search_fields=['location_name', 'campus_name'],
                                                         query_language='ko-kr',
                                                         top=1)
            message = ''
            for result in results:
                message += f"{result['location_name']}은(는) {result['campus_name']} {result['building_id']} 건물에 있으며, " \
                           + "다음 링크에서 해당 위치를 확인할 수 있습니다.\n\n" \
                           + result['location_url']

            if message == '':
                message = '죄송합니다. 관련 장소를 찾지 못했어요.'

            return {'message': message}
        elif clu_result['intent'] == 'Board':
            results = self.search_board_client.search(search_text=user_message,
                                                      query_type='semantic',
                                                      semantic_configuration_name='test',
                                                      search_fields=['NOTI_TITLE'],
                                                      query_language='ko-kr',
                                                      top=3)
            if results is not None:
                message = '네, 질문하신 내용과 관련한 게시물은 다음과 같습니다.\n\n'
                for result in results:
                    message += f"{result['NOTI_TITLE']}\n{result['NOTI_URL']}\n\n"
            else:
                message = '죄송합니다. 질문과 관련한 답변을 찾을 수가 없어요.'

            return {'message': message}

    # 메모리 반환
    def __cleanup(self):
        self.clu_client.close()
        self.qna_client.close()
        self.search_location_client.close()
        self.search_board_client.close()
