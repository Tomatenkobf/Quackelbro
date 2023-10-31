from flask import Flask, request
import yaml
import os

app = Flask(__name__)

def load_config():
    with open('/home/tomatenkobf/web/config.yaml', 'r') as f:
        return yaml.safe_load(f)
    
def config_wifi(ssid,password):
    config_path = "/etc/wpa_supplicant/wpa_supplicant.conf"

    # Überprüfen Sie, ob die Datei existiert und öffnen Sie sie
    if os.path.exists(config_path):
        with open(config_path, 'a') as file:
            # Fügen Sie die Netzwerkinformationen hinzu
            file.write('\nnetwork={\n')
            file.write('    ssid="{}"\n'.format(ssid))
            file.write('    psk="{}"\n'.format(password))
            file.write('}\n')
    else:
        print("Die Datei {} existiert nicht.".format(config_path))


@app.route('/', methods=['GET', 'POST'])
def form():
    config = load_config()
    submit_message = ''
    if request.method == 'POST':
        data = {
            'api_id': request.form.get('api_id'),
            'api_hash': request.form.get('api_hash'),
            'username': request.form.get('username'),
            'audio_gain_notification': request.form.get('audio_gain_notification'),
            'audio_gain_voice': request.form.get('audio_gain_voice'),
            'ssid': request.form.get('ssid'),
            'password': request.form.get('password'),
            'phonenumber': request.form.get('phonenumber'),
            'auth_code': request.form.get('auth_code'),
            'is_auth': 'checked' if config['is_auth'] else ''
        }
        with open('/home/tomatenkobf/web/config.yaml', 'w') as f:
            yaml.dump(data, f)

        # Konfiguration des WLANs
        #Teste, ob SSID und password verändert wurden
        if config['ssid'] != data['ssid'] and config['password'] != data['password']:
            config_wifi(data['ssid'],data['password'])
        
        submit_message = f'Saved Values :)'

        # Neustart des Raspberry Pi
        #os.system('sudo reboot')

        #return 'Values saved to config.yaml. You may now close the browser window.'
    return f'''
        <style>
            body {{ font-family: Arial, sans-serif; }}
            form {{ background: #f0f0f0; padding: 20px; border-radius: 10px; }}
            input[type="submit"] {{ background: #0099ff; color: white; padding: 5px 10px; border-radius: 5px; border: none; cursor: pointer; }}
            .message {{ margin-top: 10px;font-size: 11px; }}
        </style>

        <form method="POST">
            <div class="section">
                <h2>Telegram</h2>
                Authorization Status: <input type="checkbox" name="auth_status" {config['is_auth']} disabled><br>
                API ID: <input type="number" name="api_id" value="{config['api_id']}"><br>
                API Hash: <input type="text" name="api_hash" value="{config['api_hash']}"><br>
                Phonenumber: <input type="text" name="phonenumber" value="{config['phonenumber']}"><br>
                Auth Code: <input type="text" name="auth_code" value="{config['auth_code']}"><br>
                Messages to/from: <input type="text" name="username" value="{config['username']}"><br>
            </div>

            <div class="section">
                <h2>Audio</h2>
                Audio Gain Notification: <input type="number" step="0.1" name="audio_gain_notification" value="{config['audio_gain_notification']}"><br>
                Audio Gain Voice: <input type="number" step="0.1" name="audio_gain_voice" value="{config['audio_gain_voice']}"><br>
            </div>

            <div class="section">
                <h2>Wifi</h2>
                SSID: <input type="text" name="ssid" value="{config['ssid']}"><br>
                Password: <input type="text" name="password" value="{config['password']}"><br>
            </div>

            <input type="submit" value="Submit">
            <div class="message">{submit_message}</div>
        </form>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
