import requests
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# MySQL Config
app.config['MYSQL_HOST'] = 'db4free.net'
app.config['MYSQL_USER'] = 'payment_iae'
app.config['MYSQL_PASSWORD'] = 'payment_iae'
app.config['MYSQL_DB'] = 'payment_iae'
mysql = MySQL(app)


def get_count(va):
    cur = mysql.connection.cursor()
    query = "SELECT COUNT(*) as count FROM payment WHERE va = %s AND status = 'W';"
    cur.execute(query, [va])
    data = cur.fetchone()
    
    return data[0]

def get_payment_by_va(va):
    cur = mysql.connection.cursor()
    query = "SELECT * FROM payment WHERE va = %s AND status = 'W';"
    cur.execute(query, [va])
    data = cur.fetchone()
    
    if(data):
        return data
    else:
        return -1

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
                'payment_detail_id': detail[0],
                'trans_id': detail[2],
                'amount': detail[3],
                'time': detail[4]
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
    def payment_type(id):
        query = "SELECT * FROM payment_type WHERE payment_type_id = %s ;"
        cur.execute(query, [id])
        data = cur.fetchone()
        
        if(data):
            return data[2]
        else:
            return -1

    def add_payment_trans(id, title, status, trans_list):
        total_amount = 0

        for trans_id in trans_list:
            amount = 150000000 #Disini hit endpoint pemesanan untuk get harga
            total_amount += amount
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO payment_detail (payment_id, trans_id, amount, time) VALUES (%s, %s, %s, %s)", (id, trans_id, amount, time))
            mysql.connection.commit()
    
        cur.execute("SELECT a.admin_fee FROM payment_type a INNER JOIN payment b ON b.payment_type_id = a.payment_type_id WHERE b.payment_id = %s;", [id])
        data = cur.fetchone()
        
        response = requests.post('https://bankapi-iae.azurewebsites.net/createbankpayment', json={
            'va': va,
            'amount': total_amount + data[0],
            'title': title,
            'status': status
        })

        cur.close()

    cur = mysql.connection.cursor()
    payment_type_id = request.json['payment_type_id']
    phone = request.json['phone']
    payment_code = payment_type(payment_type_id)
    va =  int(str(payment_code) + str(phone))
    
    if(payment_code == -1):
        return jsonify({'status': False, 'status_code': 409, 'message': 'Bank Tidak Tersedia!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 409
    
    title = request.json['title']
    exp_time = request.json['expire_time']
    trans_list = request.json['product_list']
    status = "W"

    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expire = datetime.strptime(exp_time, "%H:%M:%S").time()
    expire_time = datetime.now() + timedelta(hours=expire.hour, minutes=expire.minute, seconds=expire.second)
    
    query = "SELECT * FROM payment WHERE va = %s AND status = 'W';"
    cur.execute(query, [va])
    va_checked = cur.fetchall()
    message = ""

    if va_checked:
        payment = get_payment_by_va(va)
        
        if(datetime.strptime(str(payment[7]), '%Y-%m-%d %H:%M:%S') > datetime.now()):
            payment_id = va_checked[0][0]
            total_amount = 0
            for trans_id in trans_list:
                amount = 150000000 #Disini hit endpoint pemesanan untuk get harga
                total_amount += amount
                
            response = requests.put('https://bankapi-iae.azurewebsites.net/updatebankpayment', json={
                'va': va_checked[0][3],
                'addAmount': total_amount
            })
            add_payment_trans(payment_id, title, status, trans_list)
            message = "Transaction added successfully!"
        else:
            response = requests.put('https://bankapi-iae.azurewebsites.net/updatebankpayment', json={
                'va': va,
                'status': 'E'
            })
            
            return jsonify({'status': False, 'status_code': 409, 'message': 'Pembayaran sudah expire!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 409
    else:
        cur.execute("INSERT INTO payment (payment_type_id, title, va, status, time, update_time, expire_time) VALUES ( %s, %s, %s, %s, %s, %s, %s)", (payment_type_id, title, va, status, time, update_time, expire_time))
        mysql.connection.commit()
        payment_id = cur.lastrowid
        add_payment_trans(payment_id, title, status, trans_list)
        message = "Payment created successfully!"
    
    return jsonify({'status': True, 'status_code': 201, 'message': message, 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 201

# Endpoint 4 - Submit Payment
@app.route('/confirmpayment', methods=['POST'])
def confirm_payment():
    va = request.json['va']
    status = request.json['status']

    if(status in ['W', 'S', 'C', 'E']):
        payment = get_payment_by_va(va)
        result = {'status': True, 'status_code': 200, 'message': 'Submit payment Success!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        if(payment != -1):
            if(status == 'S'):
                if(datetime.strptime(str(payment[7]), '%Y-%m-%d %H:%M:%S') < datetime.now()):
                    status = 'E'
                    
                    result = {'status': False, 'status_code': 409, 'message': 'Pembayaran sudah expire!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            response = requests.put('https://bankapi-iae.azurewebsites.net/updatebankpayment', json={
                'va': va,
                'status': status
            })
        else:
            result = {'status': False, 'status_code': 409, 'message': 'Tidak ada pembayaran yang berlangsung!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        return jsonify(result), result['status_code']
    else:
        return jsonify({'status': True, 'status_code': 409, 'message': 'Status code tidak terdaftar!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 409

# Endpoint 5 - Update Status
@app.route('/updatepaymentstatus', methods=['PUT'])
def update_status():
    va = request.json['va']
    status = request.json['status']
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = mysql.connection.cursor()
    cur.execute("UPDATE payment SET status=%s, update_time=%s WHERE va=%s AND status = 'W'", (status, update_time, va))
    mysql.connection.commit()
    return jsonify({'status': True, 'status_code': 200, 'message': 'Update status payment success!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200

# Endpoint 6 - Delete Payment Trans
@app.route('/deletepaymenttrans', methods=['DELETE'])
def delete_payment_trans():
    payment_id = request.json['payment_id']
    trans_id = request.json['pemesanan_id']
    cur = mysql.connection.cursor()
    
    query = "SELECT * FROM payment_detail WHERE payment_id = %s;"
    cur.execute(query, [payment_id])
    payment_detail = cur.fetchall()
        
    if(payment_detail):
        payment_id_rows = len(payment_detail)
        query = "SELECT * FROM payment WHERE payment_id = %s AND status = 'W';"
        cur.execute(query, [payment_detail[0][1]])
        payment = cur.fetchone()

        if(payment):
            if payment_id_rows > 1:
                amount = payment_detail[0][3]
                response = requests.put('https://bankapi-iae.azurewebsites.net/updatebankpayment', json={
                    'va': payment[3],
                    'subAmount': amount
                })
                cur.execute("DELETE FROM payment_detail WHERE trans_id=%s AND payment_id =%s", ([trans_id, payment_detail[0][1]]))
                mysql.connection.commit()
                cur.close()
                return jsonify({'status': True, 'status_code': 200, 'message': 'Transaction deleted successfully!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
            else:
                cur.execute("DELETE FROM payment_detail WHERE trans_id=%s AND payment_id =%s", ([trans_id, payment_detail[0][1]]))
                mysql.connection.commit()
                cur.execute("DELETE FROM payment WHERE payment_id=%s AND status = 'W'", ([payment_id]))
                mysql.connection.commit()
                response = requests.delete('https://bankapi-iae.azurewebsites.net/deletebankpayment', json={
                    'va': payment[3]
                })
                cur.close()
                return jsonify({'status': True, 'status_code': 200, 'message': 'Payment and transaction deleted!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 200
        else:
            return jsonify({'status': True, 'status_code': 409, 'message': 'Transaksi gagal dihapus karena tidak ada pembayaran yang sedang berlangsung!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 409
    else:
        return jsonify({'status': True, 'status_code': 409, 'message': 'Tidak ada transaksi yang berlangsung!', 'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), 409

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
