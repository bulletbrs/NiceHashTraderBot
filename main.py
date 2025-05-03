import os
import json
import time
import logging
import threading
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from nicehash import NiceHashPrivateApi

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "4a2dfa97-1fb0-4c5e-98e3-b565b29f1e35")

# Global variables for API credentials and automated orders management
api_host = "https://api2.nicehash.com"
automation_running = False
automation_thread = None
automation_interval = 60  # Default interval in seconds
automation_settings = {}
api_handler = None
background_thread_lock = threading.Lock()

def api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global api_handler
        if api_handler is None:
            flash('Please add your API credentials in Settings', 'warning')
            return redirect(url_for('settings'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    global api_handler, automation_running
    
    if api_handler is not None:
        try:
            # Get account info
            account_info = api_handler.get_account_info()
            
            # Get active orders
            active_orders = api_handler.get_my_active_orders(limit=10)
            
            # Server time
            server_time = api_handler.get_server_time()
            
            return render_template('index.html', 
                                  account_info=account_info, 
                                  active_orders=active_orders, 
                                  server_time=server_time,
                                  automation_running=automation_running)
        except Exception as e:
            logging.error(f"Error in index route: {str(e)}")
            flash(f"Error connecting to NiceHash API: {str(e)}", 'danger')
    
    return render_template('index.html', 
                          account_info=None, 
                          active_orders=None, 
                          server_time=None,
                          automation_running=automation_running)

@app.route('/orders')
@api_required
def orders():
    try:
        active_orders = api_handler.get_my_active_orders(limit=1000)
        all_orders = api_handler.get_my_all_orders(limit=100)
        return render_template('orders.html', active_orders=active_orders, all_orders=all_orders)
    except Exception as e:
        logging.error(f"Error in orders route: {str(e)}")
        flash(f"Error retrieving orders: {str(e)}", 'danger')
        return render_template('orders.html', active_orders=None, all_orders=None)
        
@app.route('/marketplace')
@api_required
def marketplace():
    try:
        # Получаем данные всех доступных алгоритмов
        algorithms_data = api_handler.get_algorithms()
        
        # Получаем доступные рынки
        markets = api_handler.get_markets()
        
        # Выбранный алгоритм и рынок
        selected_algorithm = request.args.get('algorithm', None)
        selected_market = request.args.get('market', None)
        
        # Информация о рынке
        marketplace_data = None
        
        # API требует обязательный параметр algorithm
        if selected_algorithm:
            # Получаем данные рынка для выбранного алгоритма и рынка
            marketplace_data = api_handler.get_marketplace_data(algorithm=selected_algorithm, market=selected_market)
        
        return render_template('marketplace.html', 
                              algorithms=algorithms_data, 
                              markets=markets,
                              marketplace_data=marketplace_data,
                              selected_algorithm=selected_algorithm,
                              selected_market=selected_market)
    except Exception as e:
        logging.error(f"Error in marketplace route: {str(e)}")
        flash(f"Error retrieving marketplace data: {str(e)}", 'danger')
        return render_template('marketplace.html', 
                              algorithms=None, 
                              markets=None,
                              marketplace_data=None,
                              selected_algorithm=selected_algorithm,
                              selected_market=selected_market)

@app.route('/create_order', methods=['GET', 'POST'])
@api_required
def create_order():
    if request.method == 'GET':
        try:
            # Get algorithms, pools, and markets for the form
            algorithms = api_handler.get_algorithms()
            pools = api_handler.get_pools()
            markets = api_handler.get_markets()
            
            # Получаем параметры из URL для предварительного заполнения формы
            preselected_algorithm = request.args.get('algorithm', '')
            preselected_market = request.args.get('market', '')
            preselected_price = request.args.get('price', '')
            preselected_limit = request.args.get('limit', '')
            
            return render_template('create_order.html', 
                                algorithms=algorithms, 
                                pools=pools,
                                markets=markets,
                                preselected_algorithm=preselected_algorithm,
                                preselected_market=preselected_market,
                                preselected_price=preselected_price,
                                preselected_limit=preselected_limit)
        except Exception as e:
            logging.error(f"Error loading create order page: {str(e)}")
            flash(f"Error loading order creation page: {str(e)}", 'danger')
            return redirect(url_for('index'))
    
    elif request.method == 'POST':
        try:
            # Extract form data
            algorithm = request.form['algorithm']
            market = request.form['market']
            price = request.form['price']
            limit = request.form['limit']
            amount = request.form.get('amount', None)
            
            # Pool information
            pool_option = request.form.get('pool_option')
            
            if pool_option == 'existing':
                pool_id = request.form.get('pool_id')
                response = api_handler.create_order(
                    market=market,
                    algorithm=algorithm,
                    price=price,
                    limit=limit,
                    amount=amount,
                    pool_id=pool_id
                )
            else:
                # New pool
                pool_name = request.form.get('pool_name')
                stratum_hostname = request.form.get('stratum_hostname')
                stratum_port = request.form.get('stratum_port')
                username = request.form.get('username')
                password = request.form.get('password')
                
                response = api_handler.create_order(
                    market=market,
                    algorithm=algorithm,
                    price=price,
                    limit=limit,
                    amount=amount,
                    pool_name=pool_name,
                    algorithm_name=algorithm,
                    stratum_hostname=stratum_hostname,
                    stratum_port=stratum_port,
                    username=username,
                    password=password
                )
                
            if 'success' in response and not response['success']:
                flash(f"Error creating order: {response.get('error', 'Unknown error')}", 'danger')
            else:
                flash("Order created successfully!", 'success')
                return redirect(url_for('orders'))
                
        except Exception as e:
            logging.error(f"Error creating order: {str(e)}")
            flash(f"Error creating order: {str(e)}", 'danger')
        
        return redirect(url_for('create_order'))

@app.route('/order/cancel/<order_id>', methods=['POST'])
@api_required
def cancel_order(order_id):
    try:
        response = api_handler.cancel_order(order_id)
        
        if 'success' in response and not response['success']:
            flash(f"Error cancelling order: {response.get('error', 'Unknown error')}", 'danger')
        else:
            flash("Order cancelled successfully!", 'success')
    except Exception as e:
        logging.error(f"Error cancelling order: {str(e)}")
        flash(f"Error cancelling order: {str(e)}", 'danger')
    
    return redirect(url_for('orders'))

@app.route('/order/update_price/<order_id>', methods=['POST'])
@api_required
def update_price(order_id):
    try:
        price = request.form.get('price')
        response = api_handler.set_order_price(order_id, price)
        
        if 'success' in response and not response['success']:
            flash(f"Error updating price: {response.get('error', 'Unknown error')}", 'danger')
        else:
            flash("Price updated successfully!", 'success')
    except Exception as e:
        logging.error(f"Error updating price: {str(e)}")
        flash(f"Error updating price: {str(e)}", 'danger')
    
    return redirect(url_for('orders'))

@app.route('/order/update_limit/<order_id>', methods=['POST'])
@api_required
def update_limit(order_id):
    try:
        limit = request.form.get('limit')
        response = api_handler.set_order_limit(order_id, limit)
        
        if 'success' in response and not response['success']:
            flash(f"Error updating limit: {response.get('error', 'Unknown error')}", 'danger')
        else:
            flash("Limit updated successfully!", 'success')
    except Exception as e:
        logging.error(f"Error updating limit: {str(e)}")
        flash(f"Error updating limit: {str(e)}", 'danger')
    
    return redirect(url_for('orders'))

@app.route('/order/refill/<order_id>', methods=['POST'])
@api_required
def refill_order(order_id):
    try:
        amount = request.form.get('amount')
        response = api_handler.refill_order(order_id, amount)
        
        if 'success' in response and not response['success']:
            flash(f"Error refilling order: {response.get('error', 'Unknown error')}", 'danger')
        else:
            flash("Order refilled successfully!", 'success')
    except Exception as e:
        logging.error(f"Error refilling order: {str(e)}")
        flash(f"Error refilling order: {str(e)}", 'danger')
    
    return redirect(url_for('orders'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global api_handler, api_host
    
    if request.method == 'POST':
        try:
            organization_id = request.form.get('organization_id')
            api_key = request.form.get('api_key')
            api_secret = request.form.get('api_secret')
            
            # Store API credentials in session (not recommended for production - use a database)
            session['organization_id'] = organization_id
            session['api_key'] = api_key
            session['api_secret'] = api_secret
            
            # Initialize API handler
            api_handler = NiceHashPrivateApi(
                host=api_host,
                organisation_id=organization_id,
                key=api_key,
                secret=api_secret,
                verbose=True
            )
            
            # Test API connection
            server_time = api_handler.get_server_time()
            if server_time:
                flash("API connection successful!", 'success')
            else:
                flash("API connection failed!", 'danger')
                api_handler = None
                
        except Exception as e:
            logging.error(f"Error saving API settings: {str(e)}")
            flash(f"Error saving API settings: {str(e)}", 'danger')
            api_handler = None
    
    # Get current values from session
    organization_id = session.get('organization_id', '')
    api_key = session.get('api_key', '')
    api_secret = session.get('api_secret', '')
    
    return render_template('settings.html', 
                          organization_id=organization_id, 
                          api_key=api_key,
                          api_secret=api_secret)

@app.route('/automation', methods=['GET', 'POST'])
@api_required
def automation():
    global automation_settings, automation_interval
    
    if request.method == 'POST':
        try:
            automation_settings = {
                'enabled': True,
                'interval': int(request.form.get('interval', 60)),
                'rules': []
            }
            
            # Extract rules from form
            rule_count = int(request.form.get('rule_count', 0))
            for i in range(1, rule_count + 1):
                prefix = f"rule_{i}_"
                algorithm = request.form.get(f"{prefix}algorithm", '')
                
                if not algorithm:  # Skip empty rules
                    continue
                    
                rule = {
                    'algorithm': algorithm,
                    'market': request.form.get(f"{prefix}market", ''),
                    'min_price': float(request.form.get(f"{prefix}min_price", 0)),
                    'max_price': float(request.form.get(f"{prefix}max_price", 0)),
                    'default_limit': float(request.form.get(f"{prefix}default_limit", 0)),
                    'action': request.form.get(f"{prefix}action", 'maintain')
                }
                automation_settings['rules'].append(rule)
            
            # Update automation interval
            automation_interval = automation_settings['interval']
            
            flash("Automation settings saved!", 'success')
        except Exception as e:
            logging.error(f"Error saving automation settings: {str(e)}")
            flash(f"Error saving automation settings: {str(e)}", 'danger')
    
    try:
        # Get algorithms and markets for the form
        algorithms = api_handler.get_algorithms()
        markets = api_handler.get_markets()
        
        return render_template('automation.html', 
                              automation_settings=automation_settings,
                              algorithms=algorithms,
                              markets=markets,
                              automation_running=automation_running)
    except Exception as e:
        logging.error(f"Error loading automation page: {str(e)}")
        flash(f"Error loading automation page: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/automation/start', methods=['POST'])
@api_required
def start_automation():
    global automation_running, automation_thread, background_thread_lock
    
    if not automation_settings or not automation_settings.get('rules'):
        flash("Please set up automation rules first!", 'warning')
        return redirect(url_for('automation'))
    
    with background_thread_lock:
        if not automation_running:
            automation_running = True
            automation_thread = threading.Thread(target=run_automation)
            automation_thread.daemon = True
            automation_thread.start()
            flash("Automation started!", 'success')
        else:
            flash("Automation is already running!", 'info')
    
    return redirect(url_for('automation'))

@app.route('/automation/stop', methods=['POST'])
def stop_automation():
    global automation_running
    
    automation_running = False
    flash("Automation stopped!", 'success')
    
    return redirect(url_for('automation'))

def run_automation():
    global automation_running, api_handler, automation_interval, automation_settings
    
    logging.info("Starting automation thread")
    
    while automation_running:
        try:
            if not api_handler:
                logging.error("API handler not initialized!")
                automation_running = False
                break
            
            logging.info("Running automation cycle...")
            
            # Get current active orders
            active_orders_response = api_handler.get_my_active_orders()
            
            if 'list' not in active_orders_response:
                logging.error(f"Failed to get active orders: {active_orders_response}")
                time.sleep(automation_interval)
                continue
                
            active_orders = active_orders_response['list']
            
            # Process each rule
            for rule in automation_settings.get('rules', []):
                algorithm = rule.get('algorithm')
                market = rule.get('market')
                min_price = rule.get('min_price')
                max_price = rule.get('max_price')
                default_limit = rule.get('default_limit')
                action = rule.get('action')
                
                # Find matching orders
                matching_orders = [
                    order for order in active_orders 
                    if order['algorithm']['algorithm'] == algorithm
                    and order['market'] == market
                ]
                
                if action == 'maintain' and matching_orders:
                    # Adjust existing orders
                    for order in matching_orders:
                        order_id = order['id']
                        current_price = float(order['price'])
                        
                        # Check if price adjustment needed
                        if current_price < min_price:
                            logging.info(f"Increasing price for order {order_id} from {current_price} to {min_price}")
                            api_handler.set_order_price(order_id, str(min_price))
                        elif current_price > max_price:
                            logging.info(f"Decreasing price for order {order_id} from {current_price} to {max_price}")
                            api_handler.set_order_price(order_id, str(max_price))
                
                elif action == 'create' and not matching_orders:
                    # Create new order if none exists
                    logging.info(f"Creating new order for {algorithm} in {market}")
                    
                    # TODO: Add pool information and complete order creation
                    # This is a placeholder for actual implementation
                    logging.info("Order creation in automation not implemented yet")
                    
            logging.info(f"Automation cycle completed. Sleeping for {automation_interval} seconds")
            
        except Exception as e:
            logging.error(f"Error in automation thread: {str(e)}")
        
        # Sleep until next cycle
        for _ in range(automation_interval):
            if not automation_running:
                break
            time.sleep(1)
    
    logging.info("Automation thread stopped")

@app.route('/api/account_info', methods=['GET'])
@api_required
def api_account_info():
    try:
        account_info = api_handler.get_account_info()
        return jsonify(account_info)
    except Exception as e:
        logging.error(f"Error fetching account info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/active_orders', methods=['GET'])
@api_required
def api_active_orders():
    try:
        active_orders = api_handler.get_my_active_orders()
        return jsonify(active_orders)
    except Exception as e:
        logging.error(f"Error fetching active orders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/algorithms', methods=['GET'])
@api_required
def api_algorithms():
    try:
        algorithms = api_handler.get_algorithms()
        return jsonify(algorithms)
    except Exception as e:
        logging.error(f"Error fetching algorithms: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pools', methods=['GET'])
@api_required
def api_pools():
    try:
        pools = api_handler.get_pools()
        return jsonify(pools)
    except Exception as e:
        logging.error(f"Error fetching pools: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/analytics')
@api_required
def analytics():
    try:
        # Получаем данные всех доступных алгоритмов
        algorithms_response = api_handler.get_algorithms()
        algorithms_data = []
        
        # Обработка ответа API с алгоритмами
        if algorithms_response and 'miningAlgorithms' in algorithms_response:
            algorithms_data = algorithms_response['miningAlgorithms']
            logging.debug(f"Received {len(algorithms_data)} algorithms from API")
        
        # Получаем доступные рынки
        markets = api_handler.get_markets()
        logging.debug(f"Available markets: {markets}")
        
        # Выбранный алгоритм и рынок из URL-параметров
        selected_algorithm = request.args.get('algorithm', None)
        selected_market = request.args.get('market', None)
        logging.debug(f"Selected algorithm: {selected_algorithm}, market: {selected_market}")
        
        # Переменные для хранения данных
        optimal_price_data = None
        summary_data = None
        buy_info_data = None
        algorithm_history_data = None
        
        # Если выбран алгоритм и рынок - получаем данные
        if selected_algorithm and selected_market:
            try:
                # Получаем оптимальную цену для выбранного рынка и алгоритма
                optimal_price_data = api_handler.get_order_optimal_price(selected_market, selected_algorithm)
                logging.debug(f"Optimal price data: {optimal_price_data}")
                
                # Получаем сводку по заказам для выбранного рынка и алгоритма
                summary_data = api_handler.get_orders_summary(selected_market, selected_algorithm)
                logging.debug(f"Summary data: {summary_data}")
                
                # Получаем историю за последние 24 часа (86400000 мс = 24 часа)
                now = int(time.time() * 1000)
                day_ago = now - 86400000
                algorithm_history_data = api_handler.get_algorithm_history(
                    algorithm=selected_algorithm,
                    from_timestamp=day_ago,
                    to_timestamp=now
                )
                logging.debug(f"History data points: {len(algorithm_history_data) if algorithm_history_data else 0}")
            except Exception as e:
                logging.error(f"Error fetching algorithm data: {str(e)}")
                flash(f"Error retrieving algorithm data: {str(e)}", 'warning')
        
        # Получаем общую информацию о рынке
        try:
            buy_info_data = api_handler.get_buy_info()
            logging.debug(f"Buy info received: {len(buy_info_data['miningAlgorithms']) if buy_info_data and 'miningAlgorithms' in buy_info_data else 0} algorithms")
        except Exception as e:
            logging.error(f"Error fetching buy info: {str(e)}")
            flash(f"Error retrieving market information: {str(e)}", 'warning')
        
        return render_template(
            'analytics.html', 
            algorithms=algorithms_data,
            markets=markets,
            selected_algorithm=selected_algorithm,
            selected_market=selected_market,
            optimal_price=optimal_price_data,
            summary=summary_data,
            buy_info=buy_info_data,
            algorithm_history=algorithm_history_data
        )
    except Exception as e:
        logging.error(f"Error in analytics route: {str(e)}")
        flash(f"Error retrieving analytics data: {str(e)}", 'danger')
        return render_template('analytics.html', 
                              algorithms=None, 
                              markets=None,
                              selected_algorithm=None,
                              selected_market=None,
                              optimal_price=None,
                              summary=None,
                              buy_info=None,
                              algorithm_history=None)

# Start the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
