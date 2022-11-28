from .exceptions import MissingRequiredKey
from .connection import RestfulConnection
from .common import cache

class BigCommerceAPI:
    def __init__(self, credentials: dict):
        """
        Initiate Restful API Gateway with the provided credentials
        """
        self.update_credentials(credentials)
        
    def update_credentials(self, credentials: dict):
        """
        Extract credentials and store connection
        """
        client_id, access_token, store_hash = self.extract_credentials(credentials)
        self.connection = self.build_connection(client_id, access_token, store_hash)
        
    @classmethod
    def extract_credentials(cls, credentials):
        """
        :param credentials: Credentials needed for connecting to channel.
        It should be something like:
        {
            'client_id': 'a1945b8fe6f9e21fa1595c0b51bc6405',
            'access_token': 'a1945b8fe6f9e21fa1595c0b51bc6405',
            'store_hash': '
        }
        :exception: MissingRequiredKey raises if the required keys are missing
        Required keys: client_id, access_token, store_hash
        """
        try:
            client_id = credentials['client_id']
            access_token = credentials['access_token']
            store_hash = credentials['store_hash']
            return client_id, access_token, store_hash
        except KeyError as e:
            raise MissingRequiredKey(e) from e
        
    @classmethod
    def build_connection(cls, client_id: str, access_token: str, store_hash: str):
        """
        Build connection from the provided api_key and api_secret
        """
        connection = RestfulConnection(
            scheme='https://',
            hostname='api.bigcommerce.com/',
            uri=f'stores/{store_hash}/',
            headers={
                'Content-Type': 'application/json',
                'X-Auth-Token': access_token,
                'X-Auth-Client': client_id
                
            },
        )
        return connection

@cache
def connect_with(credentials: dict):
    """
    Create a gateway for Bigcommerce connector
    """
    return BigCommerceAPI(credentials)