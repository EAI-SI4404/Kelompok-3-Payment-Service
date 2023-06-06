from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
import jwt
from functools import wraps

app = Flask(__name__)

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'payment_iae'
mysql = MySQL(app)

# Create Tables
@app.before_first_request
def create_tables():
    pass

def payment_type(id):
    if id == 1 or id == "1":
        return 3201
    elif id == 2 or id == "2":
        return 3202
    elif id == 3 or id == "3":
        return 3203
    elif id == 4 or id == "4":
        return 3204

# Endpoint 1 - GET All Payment Types
@app.route('/getallpaymenttype', methods=['GET'])
def get_all_payment_type():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM payment_type;")
    data = cur.fetchall()
    cur.close()
    
    paymentTypes = []
    for paymentType in data:
        paymentTypes.append({
            'payment_type_id': paymentType[0],
            'payment_type': paymentType[1],
            'payment_type_code': paymentType[2],
            'admin_fee': paymentType[3]
        })

    return jsonify({'paymentTypes':paymentTypes})

# Endpoint 2 - GET Payment
@app.route('/getpayment', methods=['GET'])
def get_payment():
    va = request.args.get('va')
    status = request.args.get('status') 
    cur = mysql.connection.cursor()
    query = "SELECT * FROM payment WHERE IFNULL(%s, va) = IFNULL(va, NULL) AND IFNULL(%s, status) = IFNULL(status, NULL);"
    cur.execute(query, (va, status))
    data = cur.fetchall()
    cur.close()
    
    payments = []
    for payment in data:
        payment_id = payment[0]
        payment_detail = []

        cur = mysql.connection.cursor()
        query = "SELECT * FROM payment_detail WHERE payment_id = %s ;"
        cur.execute(query, [payment_id])
        payment_detail_data = cur.fetchall()
        cur.close()

        for detail in payment_detail_data:
            payment_detail.append({
                'trans_id': detail[0],
                'amount': detail[1],
                'time': detail[2]
            })

        payments.append({
            'payment_id': payment_id,
            'payment_type_id': payment[1],
            'title': payment[2],
            'va': payment[3],
            'status': payment[4],
            'time': payment[5],
            'update_time': payment[6],
            'expire_time': payment[7],
            'payment_detail': payment_detail
        })

    return jsonify({'payments':payments})

# Endpoint 3 - Create Payment
@app.route('/createpayment', methods=['POST'])
def create_payment():
    def add_payment_trans(id):
        payment_id = id
        trans_id = request.json['pemesanan_id']
        amount = request.json['amount']
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO payment_detail (payment_id, trans_id, amount, time) VALUES ( %s, %s, %s, %s)", (payment_id, trans_id, amount, time))
        mysql.connection.commit()
        cur.close()
        
    payment_type_id = request.json['payment_type_id']
    
    title = request.json['title']
    phone = request.json['phone']
    va =  int(str(payment_type(payment_type_id)) + str(phone))
    status = "W"
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expire = datetime.strptime(request.json['expire_time'], "%H:%M:%S").time()
    expire_time = datetime.now() + timedelta(hours=expire.hour, minutes=expire.minute, seconds=expire.second)
    
    cur = mysql.connection.cursor()
    query = "SELECT * FROM payment WHERE va = %s ;"
    cur.execute(query, [va])
    
    va_checked = cur.fetchall()
    if va_checked:
        payment_id = va_checked[0][0]
        add_payment_trans(payment_id)
        return jsonify({"udah ada bang": "beres"})
    else:
        cur.execute("INSERT INTO payment (payment_type_id, title, va, status, time, update_time, expire_time) VALUES ( %s, %s, %s, %s, %s, %s, %s)", (payment_type_id, title, va, status, time, update_time, expire_time))
        mysql.connection.commit()
        payment_id = cur.lastrowid
        add_payment_trans(payment_id)
        return jsonify({"masuk bang": "beres"})
    

# Endpoint 4 - Update Status
@app.route('/updatepaymentstatus', methods=['PUT'])
def update_status():
    va = request.json['va']
    status = request.json['status']
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE payment SET status=%s, update_time=%s WHERE va=%s", (status, update_time, va))
        mysql.connection.commit()
        return jsonify({"update bang": "beres"})
    except:
        pass

# Endpoint 5 - Delete Payment Trans
@app.route('/deletepaymenttrans', methods=['DELETE'])
def delete_payment_trans():
    payment_id = request.json['payment_id']
    trans_id = request.json['pemesanan_id']
    cur = mysql.connection.cursor()
    
    query = "SELECT * FROM payment_detail WHERE payment_id = %s ;"
    cur.execute(query, [payment_id])
    payment_id_checked = cur.fetchall()
    payment_id_rows = len(payment_id_checked)
    if payment_id_rows > 1:
        cur.execute("DELETE FROM payment_detail WHERE trans_id=%s", ([trans_id]))
        mysql.connection.commit()
        cur.close()
        return jsonify({"apus bang": "beres"})
    else:
        cur.execute("DELETE FROM payment_detail WHERE trans_id=%s", ([trans_id]))
        print("anjaay")
        mysql.connection.commit()
        cur.execute("DELETE FROM payment WHERE payment_id=%s", ([payment_id]))
        mysql.connection.commit()
        cur.close()
        return jsonify({"apus bang": "beres"})
    

# Endpoint 6 - Create Bank Payment
@app.route('/createbankpayment', methods=['POST'])
def create_bank_payment():
    pass


# Endpoint 7 - Update Bank Status
@app.route('/updatebankstatus', methods=['PUT'])
def update_bank_status():
    pass

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status_code': '404 Not Found','message': 'Endpoint not found!', 'timestamp' : datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status_code': '500 Internal Server Error','message': 'Internal server error!', 'timestamp' : datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}), 500

if __name__ == '__main__':
    app.run(debug=True)
