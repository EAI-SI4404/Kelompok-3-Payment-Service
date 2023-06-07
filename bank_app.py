import requests
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'bank_iae'
mysql = MySQL(app)

# Create Tables
@app.before_first_request
def create_tables():
    pass

# Endpoint 1 - Create Bank Payment
@app.route('/createbankpayment', methods=['POST'])
def create_bank_payment():
    va =  request.json['va']
    amount = request.json['amount']
    title = request.json['title']
    status = request.json['status']
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cur = mysql.connection.cursor()
    query = "SELECT * FROM account WHERE va = %s ;"
    cur.execute(query, [va])
    
    va_checked = cur.fetchall()
    if va_checked:
        response = requests.put('http://localhost:5000/updatebankpayment', json={
        'addAmount': amount,
        'update_time': update_time,
        'va': va
    })
        return jsonify({'status_code': '201 Created', 'message': 'Transaction added successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 201
    else:
        cur.execute("INSERT INTO account ( va, amount, title,status, time, update_time) VALUES ( %s, %s, %s, %s, %s, %s)", (va, amount, title,status, time, update_time))
        mysql.connection.commit()
        cur.close()
        return jsonify({'status_code': '201 Created', 'message': 'Payment created successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 201


# Endpoint 2 - Update Bank Payment
@app.route('/updatebankpayment', methods=['PUT'])
def update_bank_status():
    json_data = request.get_json()
    va = json_data['va']
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = mysql.connection.cursor()
    if 'addAmount' in json_data:
        addAmount = json_data['addAmount']
        cur.execute("UPDATE account SET amount= amount + %s, update_time=%s WHERE va=%s", (addAmount, update_time, va))
        mysql.connection.commit()
        cur.close()
        return jsonify({'status_code': '200 OK', 'message': 'Amount addition successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
    elif 'subAmount' in json_data:
        subAmount = json_data['subAmount']
        cur.execute("UPDATE account SET amount= amount - %s, update_time=%s WHERE va=%s", (subAmount, update_time, va))
        mysql.connection.commit()
        cur.close()
        return jsonify({'status_code': '200 OK', 'message': 'Amount substraction successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
    elif 'status' in json_data:
        status = json_data['status']
        cur.execute("UPDATE account SET status=%s, update_time=%s WHERE va=%s", (status, update_time, va))
        mysql.connection.commit()
        cur.close()
        response = requests.put('http://localhost:5000/updatepaymentstatus', json={
        'va': va,
        'status': status
    })
        return jsonify({'status_code': '200 OK', 'message': 'Status updated successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200

# Endpoint 3 - Delete Bank Payment
@app.route('/deletebankpayment', methods=['DELETE'])
def delete_bank_trans():
    va = request.json['va']
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM account WHERE va=%s", (va))
    mysql.connection.commit()
    cur.close()
    return jsonify({'status_code': '200 OK', 'message': 'Bank Payment deleted successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
        

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status_code': '404 Not Found','message': 'Endpoint not found!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status_code': '500 Internal Server Error','message': 'Internal server error!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 500

if __name__ == '__main__':
    app.run(debug=True)
