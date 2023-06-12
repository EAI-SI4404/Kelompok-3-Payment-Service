import requests
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# MySQL Config
app.config['MYSQL_HOST'] = 'db4free.net'
app.config['MYSQL_USER'] = 'bank_iae'
app.config['MYSQL_PASSWORD'] = 'bank_iae'
app.config['MYSQL_DB'] = 'bank_iae'
mysql = MySQL(app)


# Endpoint 1 - Create Bank Payment
@app.route('/createbankpayment', methods=['POST'])
def create_bank_payment():
    va =  request.json['va']
    amount = request.json['amount']
    title = request.json['title']
    status = request.json['status']
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = ""
    
    cur = mysql.connection.cursor()
    query = "SELECT * FROM account WHERE va = %s AND status = 'W';"
    cur.execute(query, [va])
    
    va_checked = cur.fetchall()
    if not va_checked:
        cur.execute("INSERT INTO account ( va, amount, title,status, time, update_time) VALUES ( %s, %s, %s, %s, %s, %s)", (va, amount, title,status, time, update_time))
        mysql.connection.commit()
        cur.close()
        message = "Payment created successfully!"
    
    return jsonify({'status': True, 'status_code': 201, 'message': message, 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 201

# Endpoint 2 - Update Bank Payment
@app.route('/updatebankpayment', methods=['PUT'])
def update_bank_status():
    json_data = request.get_json()
    va = json_data['va']
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = mysql.connection.cursor()

    str_sql = ""
    message = ""
    upd_val = ""

    if 'addAmount' in json_data:
        upd_val = json_data['addAmount']
        str_sql = "UPDATE account SET amount= amount + %s, update_time=%s WHERE va=%s AND status = 'W'"
        message = "Amount addition successfully!"
    elif 'subAmount' in json_data:
        upd_val = json_data['subAmount']
        str_sql = "UPDATE account SET amount= amount - %s, update_time=%s WHERE va=%s AND status = 'W'"
        message = "Amount substraction successfully!"
    elif 'status' in json_data:
        upd_val = json_data['status']
        str_sql = "UPDATE account SET status=%s, update_time=%s WHERE va=%s AND status = 'W'"
        message = "Status updated successfully!"
        response = requests.put('https://paymentapi-iae.azurewebsites.net//updatepaymentstatus', json={
            'va': va,
            'status': upd_val
        })
    
    cur.execute(str_sql, (upd_val, update_time, va))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': True, 'status_code': 200, 'message': message, 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200

# Endpoint 3 - Delete Bank Payment
@app.route('/deletebankpayment', methods=['DELETE'])
def delete_bank_trans():
    va = request.json['va']
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM account WHERE va=%s AND status = 'W'", ([va]))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status': True, 'status_code': 200, 'message': 'Bank Payment deleted successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
        
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'status': False, 'status_code': 400,'message': 'Bad request!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': False, 'status_code': 404,'message': 'Endpoint not found!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': False, 'status_code': 500,'message': 'Internal server error!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 500

if __name__ == '__main__':
    app.run(debug=False)
