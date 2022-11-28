from . import api as bigcommerce

class BigCommerceAPIHelper:
    @classmethod
    def connect_with_account(cls, account):
        credentials = {
            'client_id': account.app_client_id,
            'access_token': account.app_access_token,
            'store_hash': account.store_hash
        }
        return cls.connect_with_dict(credentials)

    @classmethod
    def connect_with_dict(cls, credentials):
        return bigcommerce.connect_with(credentials)
