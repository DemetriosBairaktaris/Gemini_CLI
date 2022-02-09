import argparse
import requests
import hmac
import json
import hashlib
import datetime, time
import base64



def sep():
    print("___________________________________________________________________________________________________")


def get_asset_and_amount_from_result(result):
    l = []
    for item in result:
        l.append((item['currency'], item['amount']))
    return l
    pass


def print_balances(result):
    print("Here are your balances:")
    print(get_asset_and_amount_from_result(result))


def confirm_buy(order_type, amount, asset, limit_price):
    if limit_price is None:
        limit_price = "MARKET_PRICE"

    return input("type YES to buy ${} of {} at ${} >>".format(amount, asset, limit_price)) == "YES"


class ExchangeClient:

    def __init__(self, host, token, secret):
        self.host = host
        self.token = token
        self.secret = secret
        self.ALL = "all"
        self.MARKET = "MARKET"
        self.LIMIT = "exchange limit"


        self.session = requests.session()
        pass

    def create_payload(self, endpoint, **kwargs):
        t = datetime.datetime.now()
        payload_nonce = str(int(time.mktime(t.timetuple()) * 1000))
        payload = {"request": endpoint, "nonce": payload_nonce}

        for k, v, in kwargs.items():
            payload[k] = v

        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        return b64

    def create_signature(self, payload):
        encoded_secret = self.secret.encode()
        signature = hmac.new(encoded_secret, payload, hashlib.sha384).hexdigest()
        return signature
        pass

    def create_headers(self, signature, payload):
        headers = {
                "X-GEMINI-APIKEY": self.token,
                "Content-Length": "0",
                "X-GEMINI-PAYLOAD": payload,
                "X-GEMINI-SIGNATURE": signature,
                "Cache-Control": "no-cache",
                "Content-Type": "text/plain"
        }
        return headers

    def buy(self, order_type, asset, usd_amount, limit_price=None):

        if limit_price is None:
            price = float(self.prices(asset))
            price = price * 1.05
            options = ['immediate-or-cancel']
        else:
            price = float(limit_price)
            options = []


        amount_of_asset = round(float(usd_amount) / price, 4)

        endpoint = "/v1/order/new"
        payload = self.create_payload(endpoint,
                                      symbol="{}usd".format(asset),
                                      type=self.LIMIT, #orders are always limits!,
                                      side="buy",
                                      amount=str(amount_of_asset),
                                      price=str(round(price, 2)),
                                      options=options
                                      )
        signature = self.create_signature(payload)


        res = self.session.request("POST", self.host + endpoint, headers=self.create_headers(signature=signature,
                                                                                             payload=payload))
        return res.ok and not res.json()['is_cancelled']
        pass

    def sell(self, asset, usd_amount):
        pass

    def check(self, asset):
        endpoint = "/v1/balances"
        payload = self.create_payload(endpoint)
        signature = self.create_signature(payload)

        res = self.session.request("POST", self.host + endpoint, headers=self.create_headers(signature=signature,
                                                                                             payload=payload))
        return res.json()
        pass

    def prices(self, asset):
        endpoint = "/v1/pricefeed"
        res = self.session.request("GET", self.host + endpoint)
        prices = {x['pair']: x["price"] for x in res.json()}
        return prices[asset.upper() + 'USD']
        pass


def register_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, dest="token", required=True)
    parser.add_argument("--test-mode", dest="test_mode", action="store_true")
    parser.add_argument("--secret", dest="secret", type=str, required=True)
    return parser.parse_args()


def main():
    args = register_args()
    if args.test_mode:
        client = ExchangeClient("https://api.sandbox.gemini.com", args.token, args.secret)
    else:
        raise Exception("Not Implemented")

    user_input = ""


    print("Welcome to Sexy Crypto Command Line (Gemini Version)")
    print("Here are your balances:")
    print (get_asset_and_amount_from_result(client.check(client.ALL)))

    while user_input.lower() != "exit":
        print("Type 'Buy [MARKET or LIMIT] [DOLLAR AMOUNT] [SYMBOL] [LIMIT PRICE]' to buy a certain dollar amount of an asset")
        print("Type 'Check' to check your balances")
        print("Type 'Price [SYMBOL]' to get the current price of the asset")
        print("Type 'Exit' to stop this program")
        user_input = input(">>>>")
        user_input = user_input.strip()

        if user_input.lower() == "check":
            print_balances(client.check(client.ALL))

        elif user_input.lower().startswith('price'):
            user_input_tokens = user_input.split()
            _, asset = user_input_tokens
            print("Price is {}".format(client.prices(asset)))

        elif user_input.lower().startswith('buy'):
            user_input_tokens = user_input.split()
            limit_price = None
            try:
                if len(user_input_tokens) == 4:
                    _, order_type, amount_in_usd, asset = user_input_tokens
                    if order_type.lower() != "market":
                        raise
                    else:
                        order_type = client.MARKET

                    limit_price = None
                else:
                    _, order_type, amount_in_usd, asset, limit_price = user_input_tokens
                    if order_type.lower() != "limit":
                        raise ValueError
                    else:
                        order_type = client.LIMIT

            except ValueError:
                continue

            if confirm_buy(order_type, amount_in_usd, asset, limit_price=limit_price):
                print("Buying...")
                print("Bought:", client.buy(order_type, asset, amount_in_usd, limit_price))
            else:
                print("Cancelled Buy (Did not type YES)")
        else:
            print("You did not type a vaild command")

        sep()

    print("Bye Bye")




if __name__ == '__main__':
    main()

