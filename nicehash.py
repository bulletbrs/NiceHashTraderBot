import uuid
import hmac
import json
import hashlib
import time
from datetime import datetime
import requests
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class NiceHashPrivateApi:
    def __init__(self, host, organisation_id, key, secret, verbose=False):
        self.key = key
        self.secret = secret
        self.organisation_id = organisation_id
        self.host = host
        self.verbose = verbose

    def request(self, method, path, query='', body=None):
        xtime = self._get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())

        message = bytearray(self.key, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(str(xtime), 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(xnonce, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(self.organisation_id, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(method, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(path, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(query, 'utf-8')

        if body:
            body_json = json.dumps(body)
            message += bytearray('\x00', 'utf-8')
            message += bytearray(body_json, 'utf-8')

        digest = hmac.new(bytearray(self.secret, 'utf-8'), message, hashlib.sha256).hexdigest()
        xauth = self.key + ":" + digest

        headers = {
            'X-Time': str(xtime),
            'X-Nonce': xnonce,
            'X-Auth': xauth,
            'Content-Type': 'application/json',
            'X-Organization-Id': self.organisation_id,
            'X-Request-Id': str(uuid.uuid4())
        }

        s = requests.Session()
        url = self.host + path
        
        if query:
            url += '?' + query

        if self.verbose:
            logging.debug(f"Request: {method} {url}")
            if body:
                logging.debug(f"Request body: {json.dumps(body)}")

        req_id = str(uuid.uuid4())
        current_time = int(time.time() * 1000)
        logging.debug(f"req: [{req_id} {current_time} {str(uuid.uuid4())}  {str(uuid.uuid4())}  {method} {path} {query}]")
            
        if body:
            response = s.request(method, url, headers=headers, data=json.dumps(body))
        else:
            response = s.request(method, url, headers=headers)

        if self.verbose:
            logging.debug(f"Response: {response.status_code} {response.text}")
            
        logging.debug(f"res: [{response.text}]")
        
        if response.status_code >= 400:
            return {
                'success': False,
                'status_code': response.status_code,
                'error': response.text
            }
            
        if response.text:
            return response.json()
        else:
            return {'success': True}

    def get_server_time(self):
        return self.request('GET', '/api/v2/time')

    def get_my_active_orders(self, algorithm=None, market=None, ts=None, op=None, limit=None):
        # Get the current server time for the timestamp
        if ts is None:
            server_time = self.get_server_time()
            if 'serverTime' in server_time:
                ts = server_time['serverTime']
            else:
                ts = self._get_epoch_ms_from_now()
        
        # Default to 'LE' operator if not specified
        if op is None:
            op = 'LE'
        
        query_params = [
            'active=true',
            f'ts={ts}',
            f'op={op}'
        ]
        
        if algorithm:
            query_params.append(f'algorithm={algorithm}')
        if market:
            query_params.append(f'market={market}')
        if limit:
            query_params.append(f'limit={limit}')
            
        query_string = '&'.join(query_params)
        
        return self.request('GET', '/main/api/v2/hashpower/myOrders', query_string)

    def get_my_all_orders(self, algorithm=None, market=None, ts=None, op=None, limit=None):
        # Get the current server time for the timestamp
        if ts is None:
            server_time = self.get_server_time()
            if 'serverTime' in server_time:
                ts = server_time['serverTime']
            else:
                ts = self._get_epoch_ms_from_now()
        
        # Default to 'LE' operator if not specified
        if op is None:
            op = 'LE'
            
        query_params = [
            f'ts={ts}',
            f'op={op}'
        ]
        
        if algorithm:
            query_params.append(f'algorithm={algorithm}')
        if market:
            query_params.append(f'market={market}')
        if limit:
            query_params.append(f'limit={limit}')
            
        query_string = '&'.join(query_params)
        
        return self.request('GET', '/main/api/v2/hashpower/myOrders', query_string)

    def create_order(self, market, algorithm, price, limit, amount=None, pool_id=None, pool_name=None, 
                      algorithm_name=None, stratum_hostname=None, stratum_port=None, 
                      username=None, password=None, type=None, display_market_factor=None):
        """
        Create a new hashpower order
        """
        body = {
            'market': market,
            'algorithm': algorithm,
            'price': price,
            'limit': limit
        }
        
        if amount:
            body['amount'] = amount
            
        if pool_id:
            body['poolId'] = pool_id
        else:
            # Custom pool
            body['pool'] = {}
            
            if pool_name:
                body['pool']['name'] = pool_name
            
            if algorithm_name:  
                body['pool']['algorithm'] = algorithm_name
                
            if stratum_hostname:
                body['pool']['stratumHostname'] = stratum_hostname
                
            if stratum_port:
                body['pool']['stratumPort'] = stratum_port
                
            if username:
                body['pool']['username'] = username
                
            if password:
                body['pool']['password'] = password
                
        if type:
            body['type'] = type
            
        if display_market_factor:
            body['displayMarketFactor'] = display_market_factor
            
        return self.request('POST', '/main/api/v2/hashpower/order', '', body)

    def cancel_order(self, order_id):
        """
        Cancel a hashpower order
        """
        return self.request('DELETE', f'/main/api/v2/hashpower/order/{order_id}')

    def refill_order(self, order_id, amount):
        """
        Refill a hashpower order
        """
        body = {
            'amount': amount
        }
        return self.request('POST', f'/main/api/v2/hashpower/order/{order_id}/refill', '', body)

    def set_order_price(self, order_id, price, display_market_factor=None, market_factor=None):
        """
        Set the price for a hashpower order
        """
        # First get order details to retrieve market factors if not provided
        order_details = self.get_order_details(order_id)
        
        if not display_market_factor and 'displayMarketFactor' in order_details:
            display_market_factor = order_details['displayMarketFactor']
            
        if not market_factor and 'marketFactor' in order_details:
            market_factor = order_details['marketFactor']
        
        body = {
            'price': price
        }
        
        if display_market_factor:
            body['displayMarketFactor'] = display_market_factor
            
        if market_factor:
            body['marketFactor'] = market_factor
            
        return self.request('POST', f'/main/api/v2/hashpower/order/{order_id}/updatePriceAndLimit', '', body)

    def set_order_price_and_limit(self, order_id, price, limit, display_market_factor=None, market_factor=None):
        """
        Set price and limit for a hashpower order
        """
        # First get order details to retrieve market factors if not provided
        order_details = self.get_order_details(order_id)
        
        if not display_market_factor and 'displayMarketFactor' in order_details:
            display_market_factor = order_details['displayMarketFactor']
            
        if not market_factor and 'marketFactor' in order_details:
            market_factor = order_details['marketFactor']
        
        body = {
            'price': price,
            'limit': limit
        }
        
        if display_market_factor:
            body['displayMarketFactor'] = display_market_factor
            
        if market_factor:
            body['marketFactor'] = market_factor
            
        return self.request('POST', f'/main/api/v2/hashpower/order/{order_id}/updatePriceAndLimit', '', body)

    def set_order_limit(self, order_id, limit, display_market_factor=None, market_factor=None):
        """
        Set the speed limit for a hashpower order
        """
        # First get order details to retrieve market factors if not provided
        order_details = self.get_order_details(order_id)
        
        if not display_market_factor and 'displayMarketFactor' in order_details:
            display_market_factor = order_details['displayMarketFactor']
            
        if not market_factor and 'marketFactor' in order_details:
            market_factor = order_details['marketFactor']
        
        body = {
            'limit': limit
        }
        
        if display_market_factor:
            body['displayMarketFactor'] = display_market_factor
            
        if market_factor:
            body['marketFactor'] = market_factor
            
        return self.request('POST', f'/main/api/v2/hashpower/order/{order_id}/updatePriceAndLimit', '', body)

    def get_order_details(self, order_id):
        """
        Get details for a specific order
        """
        return self.request('GET', f'/main/api/v2/hashpower/order/{order_id}')

    def get_algorithms(self):
        """
        Get all available mining algorithms
        """
        return self.request('GET', '/main/api/v2/mining/algorithms')

    def get_markets(self):
        """
        Get hashpower markets (EU, USA)
        """
        # Информация о рынках есть в каждом алгоритме в поле "enabledMarkets"
        # Извлечем уникальный список рынков из всех алгоритмов
        markets = set()
        algorithms_response = self.get_algorithms()
        
        if 'miningAlgorithms' in algorithms_response:
            for algo in algorithms_response['miningAlgorithms']:
                if 'enabledMarkets' in algo:
                    # Если это строка типа "EU, USA", разделим ее
                    if isinstance(algo['enabledMarkets'], str):
                        for market in algo['enabledMarkets'].split(','):
                            markets.add(market.strip())
                    # Если это список ["EU", "USA"]
                    elif isinstance(algo['enabledMarkets'], list):
                        for market in algo['enabledMarkets']:
                            markets.add(market)
        
        # Вернем список рынков или значения по умолчанию
        if markets:
            return sorted(list(markets))
        else:
            return ['EU', 'USA'] # Значения по умолчанию, если не удалось получить список

    def get_pools(self, size=100):
        """
        Get pools information
        """
        return self.request('GET', '/main/api/v2/pools', f'size={size}')

    def create_pool(self, name, algorithm, stratum_hostname, stratum_port, username, password):
        """
        Create a new pool
        """
        body = {
            'name': name,
            'algorithm': algorithm,
            'stratumHostname': stratum_hostname,
            'stratumPort': stratum_port,
            'username': username,
            'password': password
        }
        return self.request('POST', '/main/api/v2/pool', '', body)

    def get_account_info(self):
        """
        Get account information, including balances
        """
        return self.request('GET', '/main/api/v2/accounting/accounts2')
        
    def get_marketplace_data(self, algorithm=None, market=None, size=100, page=0):
        """
        Get marketplace data for all algorithms or a specific one
        
        Hashpower order book for specified algorithm. Response contains orders for all markets and their stats.
        When there are a lot of orders, response will be paged.
        
        API Endpoint: /main/api/v2/hashpower/orderBook
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Parameters:
            algorithm (str): Mining algorithm (required)
            market (str): Filter by specific market (optional)
            size (int): Page size (optional, default: 100)
            page (int): Page number (optional, default: 0)
        """
        if not algorithm:
            return {
                'stats': [],
                'orders': []
            }
            
        query_params = [f'algorithm={algorithm}']
        
        if market:
            query_params.append(f'market={market}')
            
        query_params.append(f'size={size}')
        query_params.append(f'page={page}')
            
        query_string = '&'.join(query_params)
        
        response = self.request('GET', '/main/api/v2/hashpower/orderBook', query_string)
        
        # Форматируем данные в удобную структуру
        formatted_data = {
            'stats': [],
            'orders': []
        }
        
        if not response:
            return formatted_data
        
        # Добавляем отладочную информацию
        try:
            import logging
            logging.debug(f"API Response: {response}")
        except Exception:
            pass
            
        # Формат ответа согласно документации
        if isinstance(response, list) and len(response) > 0 and 'stats' in response[0]:
            stats_data = response[0]['stats']
            # Перебираем статистику по рынкам (EU, USA, и т.д.)
            for market_key, market_data in stats_data.items():
                # Создаем статистику по рынку
                stat_entry = {
                    'market': market_key,
                    'algorithm': {'algorithm': algorithm},
                    'speed': market_data.get('totalSpeed', '0'),
                    'displayMarketFactor': market_data.get('displayMarketFactor', 'TH'),
                    'marketFactor': market_data.get('marketFactor', '1000000000000.00000000'),
                    'priceFactor': market_data.get('priceFactor', '1000000000000.00000000'),
                    'displayPriceFactor': market_data.get('displayPriceFactor', 'TH')
                }
                formatted_data['stats'].append(stat_entry)
                
                # Добавляем все ордера в общий список
                if 'orders' in market_data:
                    for order in market_data['orders']:
                        order_data = order.copy()
                        order_data['market'] = market_key
                        # Добавляем дополнительную информацию
                        order_data['algorithm'] = {'algorithm': algorithm}
                        order_data['displayMarketFactor'] = market_data.get('displayMarketFactor', 'TH')
                        order_data['marketFactor'] = market_data.get('marketFactor', '1000000000000.00000000')
                        formatted_data['orders'].append(order_data)
        else:  # Попытка обработать другой формат ответа
            try:
                # Если ответ приходит в формате со вложенным объектом stats
                if isinstance(response, dict) and 'stats' in response:
                    stats_obj = response['stats']
                    # Проверяем, что stats_obj это словарь
                    if not isinstance(stats_obj, dict):
                        return formatted_data
                    for market_key, market_data in stats_obj.items():
                        # Создаем статистику по рынку
                        stat_entry = {
                            'market': market_key,
                            'algorithm': {'algorithm': algorithm},
                            'speed': market_data.get('totalSpeed', '0'),
                            'displayMarketFactor': market_data.get('displayMarketFactor', 'TH'),
                            'marketFactor': market_data.get('marketFactor', '1000000000000.00000000'),
                            'priceFactor': market_data.get('priceFactor', '1000000000000.00000000'),
                            'displayPriceFactor': market_data.get('displayPriceFactor', 'TH')
                        }
                        formatted_data['stats'].append(stat_entry)
                        
                        # Добавляем все ордера в общий список
                        if 'orders' in market_data:
                            for order in market_data['orders']:
                                order_data = order.copy()
                                order_data['market'] = market_key
                                # Добавляем дополнительную информацию
                                order_data['algorithm'] = {'algorithm': algorithm}
                                order_data['displayMarketFactor'] = market_data.get('displayMarketFactor', 'TH')
                                order_data['marketFactor'] = market_data.get('marketFactor', '1000000000000.00000000')
                                formatted_data['orders'].append(order_data)
            except Exception as e:
                import logging
                logging.error(f"Error parsing marketplace data: {str(e)}")
            
        return formatted_data
        
    def get_order_optimal_price(self, market, algorithm):
        """
        Get optimal current paying price for selected market and algorithm.
        
        API Endpoint: /main/api/v2/hashpower/order/price
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Parameters:
            market (str): Market (EU, USA, etc.)
            algorithm (str): Mining algorithm
        
        Returns:
            dict: Optimal price for the selected market and algorithm
        """
        query_params = [f'market={market}', f'algorithm={algorithm}']
        query_string = '&'.join(query_params)
        
        return self.request('GET', '/main/api/v2/hashpower/order/price', query_string)
    
    def get_orders_summary(self, market, algorithm):
        """
        Get accepted and rejected speed from pools and rigs, rig count and paying price for selected market and algorithm.
        
        API Endpoint: /main/api/v2/hashpower/orders/summary
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Parameters:
            market (str): Market (EU, USA, etc.)
            algorithm (str): Mining algorithm
            
        Returns:
            dict: Summary of orders for the selected market and algorithm
        """
        query_params = [f'market={market}', f'algorithm={algorithm}']
        query_string = '&'.join(query_params)
        
        return self.request('GET', '/main/api/v2/hashpower/orders/summary', query_string)
    
    def get_orders_summaries(self, market=None, algorithm=None):
        """
        Get accepted and rejected speeds for rigs and pools, rig count and paying price for selected market and/or algorithm.
        When no market or algorithm is specified all markets and algorithms are returned.
        
        API Endpoint: /main/api/v2/hashpower/orders/summaries
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Parameters:
            market (str, optional): Market (EU, USA, etc.)
            algorithm (str, optional): Mining algorithm
            
        Returns:
            dict: Summaries of orders for all markets and algorithms
        """
        query_params = []
        
        if market:
            query_params.append(f'market={market}')
            
        if algorithm:
            query_params.append(f'algorithm={algorithm}')
            
        query_string = '&'.join(query_params) if query_params else ''
        
        return self.request('GET', '/main/api/v2/hashpower/orders/summaries', query_string)
    
    def get_algorithm_history(self, algorithm, from_timestamp=None, to_timestamp=None):
        """
        Get whole history for the selected algorithm.
        
        API Endpoint: /main/api/v2/public/algo/history
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Parameters:
            algorithm (str): Algorithm code
            from_timestamp (int, optional): Range from timestamp (inclusive)
            to_timestamp (int, optional): Range to timestamp (exclusive)
            
        Returns:
            list: History of algorithm data points
        """
        query_params = [f'algorithm={algorithm}']
        
        if from_timestamp:
            query_params.append(f'fromTimestamp={from_timestamp}')
            
        if to_timestamp:
            query_params.append(f'toTimestamp={to_timestamp}')
            
        query_string = '&'.join(query_params)
        
        return self.request('GET', '/main/api/v2/public/algo/history', query_string)
    
    def get_buy_info(self):
        """
        Get information for each enabled algorithm needed for buying hashpower.
        
        API Endpoint: /main/api/v2/public/buy/info
        Documentation: https://www.nicehash.com/docs/rest/-hashpower-public
        
        Returns:
            dict: Information about algorithms, limits, prices and markets
        """
        return self.request('GET', '/main/api/v2/public/buy/info', '')

    def _get_epoch_ms_from_now(self):
        return int(time.time() * 1000)
