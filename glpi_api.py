import requests
import base64
import json
import re
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler
import os

with open("config.json") as f:
    config = json.load(f)


def get_document_id(document_item: dict):
    documents_id = []
    for items in document_item:
        documents_id.append(items["documents_id"])
    return documents_id


def get_requester(ticket_user: dict):
    requester_id = None
    for itens in ticket_user:
        if itens["type"] == 1:
            requester_id = itens["users_id"]
    return requester_id


def extract_filename(content_disposition):
    match = re.search(r'filename\*?=["\']?([^;"]+)', content_disposition)
    if match:
        return match.group(1).strip('";')
    else:
        return None


class Logger:
    def __init__(self):
        logging.basicConfig(
            handlers=[RotatingFileHandler('./logs/log.txt', maxBytes=10000000, backupCount=0)],
            level='DEBUG',
            format='[%(asctime)s] - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
        )
        logging.getLogger('schedule').propagate = False


class GLPIClient:
    """
    Classe responsável por consumir a API do GLPI
    """

    def __init__(self, user: str, password: str, token_api: str, host: str):
        self.user: str = user
        self.password: str = password
        self.token_api: str = token_api
        self.host: str = host
        self.session_token = None
        self.url: str = "http://" + self.host + "/apirest.php/"
        self.log: bool = config["glpi"]["debug_mode"]

    def _log(self, *args):
        if self.log:
            print(args)

    def init_session(self):
        api_path = "initSession"
        credencial_bytes = (self.user + ":" + self.password).encode("ascii")
        credencial_base64_bytes = base64.b64encode(credencial_bytes)
        credencial_base64 = credencial_base64_bytes.decode("UTF-8")
        credencial = "Basic " + credencial_base64
        headers = {
            "Content-Type": "application/json",
            "Authorization": credencial,
            "App-Token": self.token_api,
        }

        try:
            obj = requests.get(
                url=(self.url + api_path), headers=headers, data=None, files=None
            )
            obj_connection = json.loads(obj.text)
            session_token = obj_connection["session_token"]
            self.session_token = session_token
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao buscar o token de acesso")

    def kill_session(self) -> dict:
        api_path = "killSession"
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }

        try:
            obj = requests.get(
                url=(self.url + api_path), headers=headers, data=None, files=None
            )
            obj_connection = json.loads(obj.text)
            self.session_token = None
            return obj_connection
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao encerrar sessão")

    def get_an_item(
            self, item_name: str, item_id: int, search_filter: Optional[str] = None
    ) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        if search_filter:
            api_path = item_name + "/" + str(item_id) + "/" + search_filter
        else:
            api_path = item_name + "/" + str(item_id)
        self._log(self.url + api_path)
        try:
            response = requests.get(url=(self.url + api_path), headers=headers)
            if response.status_code == 200:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 206:
                raise Exception("Erro 206: PARTIAL CONTENT: " + response.text)
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao buscar o item {item_name}: {item_id}")

    def get_ticket_solution(self, id_ticket: int) -> dict:
        path = f"Ticket/{id_ticket}/ITILSolution/"
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        self._log(self.url + path)
        try:
            obj = requests.get(url=(self.url + path), headers=headers)
            obj_connection = json.loads(obj.text)
            return obj_connection
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao buscar a solucao do ticket {id_ticket}")

    def search_items(self, item_name: str, search_filter: str):
        """
        :param item_name: item type
        :param search_filter: filter to search. "?is_deleted=0&user=10&priority=2"
        :return: json of item
        """
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        api_path = "search/" + item_name + "/" + search_filter
        self._log(self.url + api_path, search_filter)
        try:
            response = requests.get(url=(self.url + api_path), headers=headers)
            if response.status_code == 200:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 206:
                raise Exception("Erro 206: PARTIAL CONTENT: " + response.text)
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao realizar pesquisa de itens")

    def add_item(self, item_name: str, item_data: dict):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = {"input": item_data}
        params = json.dumps(params)
        self._log(self.url + item_name, item_data)
        try:
            response = requests.post(
                url=(self.url + item_name), headers=headers, data=params
            )
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 207:
                raise Exception("Erro 207: MULTI STATUS " + response.text)
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao adicionar o item {item_name}")

    def assign_a_group_ticket(self, params: dict):
        # ex: {"input": {"tickets_id": 17160, "groups_id": 145, "type": 1}}
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = json.dumps(params)
        api_path = "Group_Ticket/"
        self._log(self.url + api_path, params)
        try:
            response = requests.post(
                url=(self.url + api_path), headers=headers, data=params
            )
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao vincular grupo ao ticket")

    def assign_a_requester_ticket(self, params: dict):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = json.dumps(params)
        api_path = "Ticket_User/"
        self._log(self.url + api_path, params)
        try:
            response = requests.post(
                url=(self.url + api_path), headers=headers, data=params
            )
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao vincular grupo ao ticket")

    def assign_a_followup_ticket(self, params: dict):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = json.dumps(params)
        self._log(self.url + "ITILFollowup", params)
        try:
            response = requests.post(
                url=(self.url + "ITILFollowup"), headers=headers, data=params
            )
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 207:
                raise Exception("Erro 207: MULTI STATUS " + response.text)
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao adicionar o ITILFollowup ao Ticket")

    def assign_a_solution_ticket(self):
        pass

    def update_item(self, item_name: str, item_id: int, params: dict):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = json.dumps(params)
        api_path = item_name + "/" + str(item_id)
        self._log(self.url + api_path, params)
        try:
            response = requests.patch(
                url=(self.url + api_path), headers=headers, data=params
            )
            if response.status_code == 200:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 207:
                raise Exception("Erro 207: MULTI STATUS " + response.text)
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(
                f"Ocorreu o erro {e} ao realizar update do item {item_name}/{item_id}"
            )

    def delete_item(self, item_name: str, params: dict):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = json.dumps(params)
        self._log(self.url + item_name, params)
        try:
            response = requests.patch(
                url=(self.url + item_name), headers=headers, data=params
            )
            if response.status_code == 200:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 204:
                raise Exception("Erro 204: NO CONTENT")
            elif response.status_code == 207:
                raise Exception("Erro 207: MULTI STATUS " + response.text)
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao realizar delete do item {item_name}")

    def create_relationship_ticket(self, father_ticket: int, children_ticket: int):
        headers = {
            "Content-Type": "application/json",
            "Session-Token": self.session_token,
            "App-Token": self.token_api,
        }
        params = {
            "input": {
                "tickets_id_1": children_ticket,
                "tickets_id_2": father_ticket,
                "link": 3,
            }
        }
        params = json.dumps(params)
        api_path = "Ticket_Ticket/"
        self._log(
            self.url + api_path, "tickets:", str(father_ticket), str(children_ticket)
        )
        try:
            response = requests.post(
                url=(self.url + api_path), headers=headers, data=params
            )
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 400:
                raise Exception(
                    "Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text
                )
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao criar relação entre tickets")

    def upload_document_file(self, document_file_path: str, name: str):
        headers = {"Session-Token": self.session_token,
                   "App-Token": self.token_api}
        upload_manifest = {"input": {
            "name": name,
            "_filename": [document_file_path]
        }}

        upload_manifest_json = json.dumps(upload_manifest)
        files = {'uploadManifest': (None, upload_manifest_json, 'application/json'),
                 'filename[0]': (document_file_path, open(document_file_path, 'rb'),
                                 'application/octet-stream')}
        self._log(self.url + "Document", name)
        try:
            response = requests.post(url=(self.url + "Document"), headers=headers, params=None, files=files)
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 400:
                raise Exception("Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text)
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro: {e} ao realizar upload do arquivo {name}")

    def download_document_file(self, item_name: str, item_id: int):
        headers = {"Content-Type": "application/json",
                   "Session-Token": self.session_token,
                   "App-Token": self.token_api,
                   "Accept": "application/octet-stream"}
        api_path = item_name + "/" + str(item_id)
        self._log(self.url + api_path, 'DONWLOAD')
        try:
            response = requests.get(url=(self.url + api_path), headers=headers)
            if response.status_code == 200:
                content_disposition = response.headers.get("content-disposition")
                name = content_disposition.split("filename=")[-1].strip('";')
                file_name = extract_filename(name)
                if not os.path.exists("./Documents"):
                    os.makedirs("./Documents")
                save_path = os.path.join("./Documents", file_name)
                with open(save_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                return file_name
            elif response.status_code == 400:
                raise Exception("Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text)
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao realizar download do item {item_name}")

    def add_document_to_item(self, params: dict):
        headers = {"Content-Type": "application/json",
                   "Session-Token": self.session_token,
                   "App-Token": self.token_api}
        params = json.dumps(params)
        self._log(self.url + "Document/1/Document_Item", params)

        try:
            response = requests.post(url=(self.url + "Document/1/Document_Item"), headers=headers, data=params)
            if response.status_code == 201:
                obj_response = json.loads(response.text)
                return obj_response
            elif response.status_code == 400:
                raise Exception("Erro 400: BAD REQUEST\nMensagem de Erro: " + response.text)
            elif response.status_code == 401:
                raise Exception("Erro 401: UNAUTHORIZED")
        except Exception as e:
            self._log(f"Ocorreu o erro {e} ao adicionar o item Document_Item")
