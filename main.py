import logging
from datetime import datetime
from flask import Flask, jsonify, session, url_for, redirect, render_template, request, send_from_directory
from subprocess import call
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import configparser
import os.path

config = configparser.ConfigParser()

# logger instance 생성
logger = logging.getLogger(__name__)

# handler 생성 (stream, file)
# streamHandler = logging.StreamHandler()
fileHandler = logging.FileHandler('./logs/vote-log.log')

# logger instance에 handler 설정
# logger.addHandler(streamHandler)
logger.addHandler(fileHandler)

logging.basicConfig(encoding='utf-8', level=logging.DEBUG)


app = Flask(__name__, static_url_path='', static_folder='templates/static',)
app.secret_key = "mysecret"

socket_io = SocketIO(app)

number1 = 0
number2 = 0
ID = ''
PW = ''

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         session['name'] = request.form['name']
#         session['room'] = request.form['room']
#         return redirect(url_for('chat'))
#     return render_template('index.html')
# @app.route('/assets/<path:path>')
# def send_report(path):
#     return send_from_directory('assets', path)

@app.route('/')
def index():
    return render_template('view-only.html', num1=number1, num2=number2)

@app.route('/per')
def percentagev():
    if number1+number2 != 0:
        per1 = round(number1/(number1+number2)*100)
        per2 = round(number2/(number1+number2)*100)
    else:
        per1 = 50
        per2 = 50

    return render_template('view-only-per.html', num1=number1, num2=number2, per1=per1, per2=per2)

@app.route('/per-g')
def percentagevg():
    if number1+number2 != 0:
        per1 = round(number1/(number1+number2)*100)
        per2 = round(number2/(number1+number2)*100)
    else:
        per1 = 50
        per2 = 50
    return render_template('view-only-per-g.html', num1=number1, num2=number2, per1=per1, per2=per2)

@app.route('/view-rotate')
def rotatev():
    return render_template('view-rotate.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # session['name'] = request.form['name']
        # session['room'] = request.form['room']
        if ID == request.form['id'] and PW == request.form['pw']:
            return render_template('admin-page.html', num1=number1, num2=number2)
        return render_template('./login/login.html', gotoname='관리자페이지', gotourl='/admin', errortext='잘못된 계정')
    return render_template('./login/login.html', gotoname='관리자페이지', gotourl='/admin', errortext='')


@app.route('/master-view', methods=['GET', 'POST'])
def maseter_view():
    if request.method == 'POST':
        # session['name'] = request.form['name']
        # session['room'] = request.form['room']
        if ID == request.form['id'] and PW == request.form['pw']:
            return render_template('view.html', num1=number1, num2=number2)
        return render_template('./login/login.html', gotoname='마스터뷰', gotourl='/master-view', errortext='잘못된 계정')
    return render_template('./login/login.html', gotoname='마스터뷰', gotourl='/master-view', errortext='')


# @app.route('/chat')
# def chat():
#     name = session.get('name', '')
#     room = session.get('room', '')
#     if name == '' or room == '':
#         return redirect(url_for('.index'))
#     return render_template('chat.html', name=name, room=room)

# @app.route('/chat')
# def chatting():
#     return render_template('chat-o.html')

@socket_io.on('joined', namespace='/votesocket')
def joined(message):
    now = datetime.now()
    ip_address = request.remote_addr
    ua = request.user_agent.string
    log_text = '[' + now.strftime('%Y-%m-%d %H:%M:%S') + '] 시스템 신규 접속 - 권한: ' + message['auth'] + ' - ' + ip_address
    logger.info(log_text+' ( '+ua+' )')
    emit('log', {'msg': log_text}, broadcast=True)


@socket_io.on('voted', namespace='/votesocket')
def voted(message):
    global number1, number2
    if message['num'] == 1:
        number1 += 1
    elif message['num'] == 2:
        number2 += 1
    save_data()
    emit('status', {'num1': number1, 'num2': number2, 'per1': round(number1/(number1+number2)*100), 'per2': round(number2/(number1+number2)*100)}, broadcast=True)

    now = datetime.now()
    ip_address = request.remote_addr
    ua = request.user_agent.string
    log_text = '[' + now.strftime('%Y-%m-%d %H:%M:%S') + '] 투표 진행 (투표기호: ' + str(message['num']) +') 현재상태: (' + str(number1) + ':' + str(number2) + ') - 권한: ' + message['auth'] + ' - ' + ip_address
    logger.info(log_text + ' ( ' + ua + ' )')
    emit('log', {'msg': log_text}, broadcast=True)


@socket_io.on('solve-error', namespace='/votesocket')
def solve_error(message):
    global number1, number2
    if message['num'] == 1:
        if not number1 <= 0:
            number1 -= 1
    elif message['num'] == 2:
        if not number2 <= 0:
            number2 -= 1
    save_data()
    emit('status', {'num1': number1, 'num2': number2, 'per1': round(number1/(number1+number2)*100), 'per2': round(number2/(number1+number2)*100)}, broadcast=True)

    now = datetime.now()
    ip_address = request.remote_addr
    ua = request.user_agent.string
    log_text = '[' + now.strftime('%Y-%m-%d %H:%M:%S') + '] 투표수 수정 (-1) (투표기호: ' + str(message['num']) +') 현재상태: (' + str(number1) + ':' + str(number2) + ') - 권한: ' + message['auth'] + ' - ' + ip_address
    logger.info(log_text + ' ( ' + ua + ' )')
    emit('log', {'msg': log_text}, broadcast=True)

# @socket_io.on('left', namespace='/votesocket')
# def left(message):
#     room = session.get('room')
#     leave_room(room)
#     emit('status', {'msg': session.get('name') + '님이 퇴장하셨습니다 (나가기)'}, room=room)

@socket_io.on("disconnect", namespace='/votesocket')
def disconnnect_user():
    # emit('status', {'msg': session.get('name') + '님이 퇴장하셨습니다'}, room=room)
    now = datetime.now()
    ip_address = request.remote_addr
    ua = request.user_agent.string
    log_text = '[' + now.strftime('%Y-%m-%d %H:%M:%S') + '] client 접속 끊김 - ' + ip_address
    logger.info(log_text + ' ( ' + ua + ' )')
    emit('log', {'msg': log_text}, broadcast=True)

# @socket_io.on("message")
# def request(message):
#     print("message : "+ message)
#     to_client = dict()
#     if message == 'new_connect':
#         to_client['message'] = "새로운 유저가 난입하였다!!"
#         to_client['type'] = 'connect'
#     else:
#         to_client['message'] = message
#         to_client['type'] = 'normal'
#     # emit("response", {'data': message['data'], 'username': session['username']}, broadcast=True)
#     send(to_client, broadcast=True)
#
#
# @socket_io.on("disconnect")
# def disconnnect_user():
#     # print("message : "+ message)
#     to_client = dict()
#     to_client['message'] = "유저가 채팅방을 나갔습니다. "
#     to_client['type'] = 'disconnect'
#     send(to_client, broadcast=True)

def get_ini():
    global ID, PW
    config = configparser.ConfigParser()
    if os.path.isfile("./Settings/account.ini"):
        config.read('./Settings/account.ini')
        sec = config.sections()
        # print(sec)
        # print('admin-account' in config)
        if 'admin-account' in config:
            if ('ID' in config['admin-account']) and ('PW' in config['admin-account']) and (
                    config['admin-account']['ID'] != '') and (config['admin-account']['PW'] != ''):
                ID = config['admin-account']['ID']
                PW = config['admin-account']['PW']
            else:
                if not ('ID' in config['admin-account']) or (config['admin-account']['ID'] == ''):
                    config['admin-account']['ID'] = 'admin'
                if not ('PW' in config['admin-account']) or (config['admin-account']['PW'] == ''):
                    config['admin-account']['PW'] = 'admin*'
                with open('./Settings/account.ini', 'w') as configfile:
                    config.write(configfile)
                ID = config['admin-account']['ID']
                PW = config['admin-account']['PW']
        else:
            config['admin-account'] = {}
            config['admin-account']['ID'] = 'admin'
            config['admin-account']['PW'] = 'admin*'
            with open('./Settings/account.ini', 'w') as configfile:
                config.write(configfile)
            ID = config['admin-account']['ID']
            PW = config['admin-account']['PW']
    else:
        config['admin-account'] = {}
        config['admin-account']['ID'] = 'admin'
        config['admin-account']['PW'] = 'admin*'
        with open('./Settings/account.ini', 'w') as configfile:
            config.write(configfile)
        ID = config['admin-account']['ID']
        PW = config['admin-account']['PW']

    # print(ID, ' ', PW)


def get_data():
    global number1, number2
    config = configparser.ConfigParser()
    if os.path.isfile("./Settings/votes.ini"):
        config.read('./Settings/votes.ini')
        sec = config.sections()
        # print(sec)
        # print('admin-account' in config)
        if 'vote-data' in config:
            if ('num1' in config['vote-data']) and ('num2' in config['vote-data']) and (
                    config['vote-data']['num1'] != '') and (config['vote-data']['num2'] != ''):
                number1 = int(config['vote-data']['num1'])
                number2 = int(config['vote-data']['num2'])
            else:
                if not ('num1' in config['vote-data']) or (config['vote-data']['num1'] == ''):
                    config['vote-data']['num1'] = '0'
                if not ('num2' in config['vote-data']) or (config['vote-data']['num2'] == ''):
                    config['vote-data']['num2'] = '0'
                with open('./Settings/votes.ini', 'w') as configfile:
                    config.write(configfile)
                number1 = int(config['vote-data']['num1'])
                number2 = int(config['vote-data']['num2'])
        else:
            config['vote-data'] = {}
            config['vote-data']['num1'] = '0'
            config['vote-data']['num2'] = '0'
            with open('./Settings/votes.ini', 'w') as configfile:
                config.write(configfile)
            number1 = int(config['vote-data']['num1'])
            number2 = int(config['vote-data']['num2'])
    else:
        config['vote-data'] = {}
        config['vote-data']['num1'] = '0'
        config['vote-data']['num2'] = '0'
        with open('./Settings/votes.ini', 'w') as configfile:
            config.write(configfile)
        number1 = int(config['vote-data']['num1'])
        number2 = int(config['vote-data']['num2'])


def save_data():
    global number1, number2
    config = configparser.ConfigParser()
    config['vote-data'] = {}
    config['vote-data']['num1'] = str(number1)
    config['vote-data']['num2'] = str(number2)
    with open('./Settings/votes.ini', 'w') as configfile:
        config.write(configfile)



if __name__ == '__main__':
    get_ini()
    get_data()
    socket_io.run(app, debug=True, host='0.0.0.0', port=9999)
