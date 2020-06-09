import requests
import json
import os
import quantumrandom
import asyncio

os.environ['WEB3_INFURA_PROJECT_ID'] = '90af2ec8351c43f9b82b17026d01a9a1'
os.environ['WEB3_INFURA_API_SECRET'] = '4c1dd095f5e7411c9b71668b6770e0be'
from web3.auto.infura import w3
import numpy as np

with open('Chi.abi', 'r') as chi_abi_file:
    chi_abi = json.load(chi_abi_file)
with open('Gst2.abi', 'r') as gst2_abi_file:
    gst2_abi = json.load(gst2_abi_file)

one_inch_split_abi = json.load(open('SplitContract.abi', 'r'))
mcd_abi = json.load(open('JoinContract.abi', 'r'))
token_abi = json.load(open('Token.abi', 'r'))

with open('PrivateKey') as privateKeyFile:
    privateKey = privateKeyFile.read()

chi_contract_address = w3.toChecksumAddress('0x0000000000004946c0e9F43F4Dee607b0eF1fA1c')
gst2_contract_address = w3.toChecksumAddress('0x0000000000b3F879cb30FE243b4Dfee438691c04')
one_inch_split_contract = w3.toChecksumAddress('0xC586BeF4a0992C495Cf22e1aeEE4E446CECDee0E')

from web3 import middleware
from web3.gas_strategies.time_based import fast_gas_price_strategy

loop = asyncio.get_event_loop()


class OneInch:
    def __init__(self):
        # json list of tokens
        self.tokens = any

    def list_tokens(self):
        if not self.config_check():
            return
        print("Tokens".format(self.tokens))

    def load_tokens(self):
        response = requests.get('https://api.1inch.exchange/v1.1/tokens')
        print("Loading tokens, status Code: {}".format(response.status_code))
        self.tokens = json.loads(response.text)

    def token_info(self, token):
        if not self.config_check():
            return
        for key, value in self.tokens.items():
            if key.lower() == token.lower():
                print(value)
                return
        print("Not Found")

    def generate_address(self):
        private_key = w3.eth.account.create(quantumrandom.hex(1000, 1000))
        print(private_key.address)
        private_key_file = open("PrivateKey", "w")
        private_key_file.write(private_key.privateKey.hex())
        private_key_file.close()
        self.privateKey = privateKeyFile.read()
        print("Private key written to file, take care it's in plain text. "
              "Calling this function again will overwrite it.")

    def print_current_pub_address(self):
        if not self.config_check():
            return
        account = w3.eth.account.privateKeyToAccount(privateKey)
        print(account.address)

    def print_current_balance(self):
        if not self.config_check():
            return
        account = w3.eth.account.privateKeyToAccount(privateKey)
        print("Current Balance: {}".format(w3.fromWei(w3.eth.getBalance(account.address), 'ether')))

    def print_current_token_balance(self, token):
        if not self.config_check():
            return
        try:
            token_contract = w3.eth.contract(address=w3.toChecksumAddress(self.get_token_info(token)["address"]),
                                             abi=token_abi)
            token_balance = token_contract.functions.balanceOf(self.get_public_key()).call()
            token_balance_normalized = w3.fromWei(int(token_balance), 'ether')
            print("Current Balance: {} {}".format(token_balance_normalized, token))
        except:
            print("Token not supported")

    @asyncio.coroutine
    async def fetch(self, from_token, to_token, quantity, blocker, focus):
        request = 'https://api.1inch.exchange/v1.1/quote?fromTokenSymbol={0}&' \
                  'toTokenSymbol={1}&amount={2}&disabledExchangesList=\'{3}\''.format(from_token, to_token, quantity,
                                                                                      blocker)
        return focus, requests.get(request)

    def api_arbitrage_detector(self, from_token, to_token, quantity):
        try:
            tasks = [self.fetch(from_token, to_token, quantity, "", "")]
            focus, swap_from_result = loop.run_until_complete(asyncio.gather(*tasks))[0]
            if swap_from_result.status_code != 200:
                print("Failure getting initial quote")
                return
            print(str(w3.fromWei(int(swap_from_result.json()['fromTokenAmount']), 'ether')) +
                  " " + swap_from_result.json()['fromToken']['symbol'] + " to " +
                  str(w3.fromWei(int(swap_from_result.json()['toTokenAmount']), 'ether')) +
                  " " + swap_from_result.json()['toToken']['symbol'])

            exchanges = requests.get('https://api.1inch.exchange/v1.1/exchanges')
            hide = ""
            for exchange in exchanges.json():
                hide += exchange["name"] + ","
            block_splits = hide[0:len(hide) - 2].split(",")

            blockers = []

            blocker_1_copy = block_splits.copy()
            blocker_1_copy.remove('Uniswap')
            blockers.append(blocker_1_copy)

            blocker_2_copy = block_splits.copy()
            blocker_2_copy.remove('Curve.fi v2')
            blockers.append(blocker_2_copy)

            blocker_3_copy = block_splits.copy()
            blocker_3_copy.remove('Curve.fi')
            blockers.append(blocker_3_copy)

            blocker_4_copy = block_splits.copy()
            blocker_4_copy.remove('MultiSplit')
            blockers.append(blocker_4_copy)

            blocker_5_copy = block_splits.copy()
            blocker_5_copy.remove('Balancer')
            blockers.append(blocker_5_copy)

            blocker_6_copy = block_splits.copy()
            blocker_6_copy.remove('Kyber')
            blockers.append(blocker_6_copy)

            tasks = []
            for blocker in blockers:
                tasks.append(
                    self.fetch(to_token, from_token, int(swap_from_result.json()['toTokenAmount']), ",".join(blocker),
                               self.diff(blocker, block_splits)))
            results = loop.run_until_complete(asyncio.gather(*tasks))
            for result in filter(lambda result: result[1].status_code == 200, results):
                swap_to_json = result[1].json()
                print(str(w3.fromWei(int(swap_to_json['fromTokenAmount']), 'ether')) +
                      " " + swap_to_json['fromToken']['symbol'] + " to " +
                      str(w3.fromWei(int(swap_to_json['toTokenAmount']), 'ether')) +
                      " " + swap_to_json['toToken']['symbol'] + ": " + result[0])
                if int(swap_to_json['toTokenAmount']) > int(swap_from_result.json()['fromTokenAmount']):
                    print("Arbitrage Detected for: {}".format(result[0]))
                    return
            print("No Arbitrage Opportunity Detected")
        except Exception as e:
            print(e)

    def quote(self, from_token, to_token, quantity):
        if not self.config_check():
            return
        one_inch_join = w3.eth.contract(address=one_inch_split_contract, abi=one_inch_split_abi)
        contract_response = one_inch_join.functions.getExpectedReturn(
            w3.toChecksumAddress(self.get_token_info(from_token)["address"]),
            w3.toChecksumAddress(self.get_token_info(to_token)["address"]), quantity, 100, 0).call(
            {'from': self.get_public_key()})
        print("Swap Quote: {0}".format(contract_response))
        return contract_response

    def swap(self, from_token, to_token, quantity):
        if not self.config_check():
            return
        account = w3.eth.account.privateKeyToAccount(privateKey)
        quote = self.quote(from_token, to_token, quantity)
        min_return = quote[0]

        # list of dist across exchanges like: [99, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        distribution = quote[1]

        # use all available exchanges
        disable_flags = 0

        # load our contract
        one_inch_join = w3.eth.contract(address=one_inch_split_contract, abi=one_inch_split_abi)

        # get our nonce
        nonce = w3.eth.getTransactionCount(self.get_public_key())

        print("From Token Info: {}".format(self.get_token_info(from_token)))
        print("To Token Info: {}".format(self.get_token_info(to_token)))

        if from_token.lower() == "eth":
            value = quantity
        else:
            value = 0

        data = one_inch_join.encodeABI(fn_name="swap", args=[
            w3.toChecksumAddress(self.get_token_info(from_token)["address"]),
            w3.toChecksumAddress(self.get_token_info(to_token)["address"]),
            quantity, min_return, distribution, disable_flags])

        tx = {
            'nonce': nonce,
            'to': one_inch_split_contract,
            'value': value,
            'gasPrice': w3.toWei(40, 'gwei'),
            'from': self.get_public_key(),
            'data': data
        }

        try:
            gas = w3.eth.estimateGas(tx)
            print("Gas Supplied: {}".format(gas))
            tx["gas"] = gas
        except Exception as e:
            print(e)
            return

        print('transaction data: {0}'.format(tx))

        try:
            signed_tx = w3.eth.account.signTransaction(tx, account.privateKey)
        except Exception as e:
            print(e)
            return False
        try:
            tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
            print("TXID: {0}".format(w3.toHex(tx_hash)))
        except Exception as e:
            print(e)
            return False

    def get_allowance(self, token):
        if not self.config_check():
            print("Call load first to populate tokens")
            return
        token_info = self.get_token_info(token)["address"]
        token_address = w3.toChecksumAddress(token_info)
        mcd_contract = w3.eth.contract(address=token_address, abi=mcd_abi)
        allowance = mcd_contract.functions.allowance(self.get_public_key(), one_inch_split_contract).call()
        print("Current allowance: {0}".format(allowance))
        return allowance

    def approve_tokens(self, token, amount):
        if not self.config_check():
            return
        token_address = w3.toChecksumAddress(self.get_token_info(token)["address"])
        mcd_contract = w3.eth.contract(address=token_address, abi=mcd_abi)
        self.get_allowance(token)
        base_account = w3.eth.account.privateKeyToAccount(privateKey)
        nonce = w3.eth.getTransactionCount(base_account.address)
        data = mcd_contract.encodeABI(fn_name="approve", args=[one_inch_split_contract, amount])
        tx = {
            'nonce': nonce,
            'to': token_address,
            'value': 0,
            'gasPrice': w3.toWei(40, 'gwei'),
            'from': base_account.address,
            'data': data
        }

        try:
            gas = w3.eth.estimateGas(tx)
            print("Gas Supplied: {}".format(gas))
            tx["gas"] = gas
        except Exception as e:
            print(e)
            return

        try:
            signed_tx = w3.eth.account.signTransaction(tx, privateKey)
        except Exception as e:
            print(e)
            return
        try:
            tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
            print("TXID from 1 Inch: {0}".format(w3.toHex(tx_hash)))
        except Exception as e:
            print(e)
            return

    def get_token_info(self, token):
        if not self.config_check():
            return
        for key in self.tokens:
            if key.lower() == token.lower():
                return self.tokens[key]

    def get_public_key(self):
        if not self.config_check():
            return
        account = w3.eth.account.privateKeyToAccount(privateKey)
        return w3.toChecksumAddress(account.address)

    @staticmethod
    def format_float(num):
        return np.format_float_positional(num, trim='-')

    @staticmethod
    def diff(li1, li2):
        li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2]
        return li_dif

    def config_check(self):
        private_key_exists = len(privateKey) != 0
        tokens_populated = self.tokens != any
        if not private_key_exists:
            print("Generate a new private key")
        if not tokens_populated:
            print("Load tokens please")
        return private_key_exists and tokens_populated


if __name__ == '__main__':

    oneInch = OneInch()
    print("Web3 Connected: {}".format(w3.isConnected()))
    # oneInch.load_tokens()
    w3.middleware_onion.add(middleware.time_based_cache_middleware)
    w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
    w3.middleware_onion.add(middleware.simple_cache_middleware)
    w3.eth.setGasPriceStrategy(fast_gas_price_strategy)
    while True:
        action = input("\nWhat should I do?\n[LIST]List Tokens\n[LOAD]Load Tokens\n[GENERATE] generate new private key"
                       "\n[PRINT] print current pub address\n[APPROVE] approve token for swap (format: approve <token> <quantity>)\n[QUOTE] request a quote using the 1inch contract (format: quote <from_token> <to_token> <quantity>)"
                       "\n[BALANCE] print current Eth balance (format: balance)"
                       "\n[TOKENBALANCE] print current token balance (format: tokenbalance <token>)\n[API] probe 1inch for an arbitrage opportunity (format: api <from_token> <to_token> <quantity>)"
                       "\n[ALLOWANCE] check allowance for a specific token (format: allowance <token>)\n[TOKEN] print token info (format: token <token>)\n[SWAP] performs an actual swap, if from_token is not Eth, don't forget to approve first (format: swap <from_token> <to_token> <quantity>)").upper()
        if action == 'LIST':
            oneInch.list_tokens()
        elif action == 'LOAD':
            oneInch.load_tokens()
        elif action == "GENERATE":
            oneInch.generate_address()
        elif action.startswith("TOKENBALANCE"):
            oneInch.print_current_token_balance(action[12:].strip())
        elif action.startswith("TOKEN"):
            oneInch.token_info(action[5:].strip())
        elif action == "PRINT":
            oneInch.print_current_pub_address()
        elif action == "BALANCE":
            oneInch.print_current_balance()
        elif action.lower().startswith("APPROVE".lower()):
            splits = action[7:].strip().split()
            if len(splits) < 2:
                print("required format \"quote {fromToken} {toToken} {quantity} \"")
            else:
                oneInch.approve_tokens(splits[0], w3.toWei(float(splits[1]), 'ether'))
        elif action.lower().startswith("API".lower()):
            splits = action[3:].strip().split()
            if len(splits) < 3:
                print("required format \"quote {fromToken} {toToken} {quantity} \"")
            else:
                oneInch.api_arbitrage_detector(splits[0], splits[1], w3.toWei(float(splits[2]), 'ether'))
        elif action.lower().startswith("QUOTE".lower()):
            splits = action[5:].strip().split()
            if len(splits) < 3:
                print("required format \"quote {fromToken} {toToken} {quantity} \"")
            else:
                oneInch.quote(splits[0], splits[1], w3.toWei(float(splits[2]), 'ether'))
        elif action.lower().startswith("SWAP".lower()):
            splits = action[4:].strip().split()
            if len(splits) < 3:
                print("required format \"quote {fromToken} {toToken} {quantity} \"")
            else:
                oneInch.swap(splits[0], splits[1], w3.toWei(float(splits[2]), 'ether'))
        elif action.lower().startswith("ALLOWANCE".lower()):
            oneInch.get_allowance(action[9:].strip())
        else:
            print("Operation Not Defined")
