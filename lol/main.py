import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
import random
import shutil
import string
import datetime
from werkzeug.utils import secure_filename
from auth import auth_routes

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET')

# Blueprint für die Authentifizierungs-Routen registrieren
app.register_blueprint(auth_routes)

CLOUD_FOLDER_LOCAL = r'F:\UPLOADS'

@app.before_request
def make_session_permanent():
    session.permanent = True

def is_logged_in() -> bool:
    return 'user' in session

def init_cloud_folder() -> str:
    if 'user' in session:
        cloud_folder = os.path.join(CLOUD_FOLDER_LOCAL, session['user']['id'])
        if not os.path.exists(cloud_folder):
            os.makedirs(cloud_folder)
        return cloud_folder
    return None

def check_terms_accepted() -> bool:
    return session.get('terms_accepted', False)

def generate_unique_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user_storage_usage() -> int:
    user_folder = init_cloud_folder()
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(user_folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

@app.route('/')
def home():
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    files = os.listdir(init_cloud_folder())
    files = [file for file in files if not file.startswith('!')]
    return render_template('home.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    user_storage_usage = get_user_storage_usage()
    storage_limit = 5 * 1024 * 1024 * 1024  # 5GB in Bytes

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(init_cloud_folder(), filename)
            file_size = file.content_length

            if user_storage_usage + file_size > storage_limit:
                flash('Speicherlimit erreicht. Bitte löschen Sie einige Dateien, um mehr hochzuladen.')
                return redirect('/upload')

            description = request.form.get('description', '')
            thumbnail = request.files.get('thumbnail')

            # Speichern der Datei
            file.save(file_path)

            # Optional: Speichern der Beschreibung und des Thumbnails
            # Beschreibung in eine separate Datei, z.B. als Textdatei
            if description:
                with open(os.path.join(init_cloud_folder(), filename + '.txt'), 'w') as desc_file:
                    desc_file.write(description)

            # Thumbnail speichern, falls vorhanden
            if thumbnail:
                thumbnail.save(os.path.join(init_cloud_folder(), 'thumbnails', secure_filename(thumbnail.filename)))

            return redirect('/')

    return render_template('upload.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    user_storage_usage = get_user_storage_usage()
    storage_limit = 5 * 1024 * 1024 * 1024  # 5GB in Bytes
    storage_usage_percentage = (user_storage_usage / storage_limit) * 100

    if request.method == 'POST':
        if 'delete_account' in request.form:
            user_folder = init_cloud_folder()
            if os.path.exists(user_folder):
                shutil.rmtree(user_folder)
            session.pop('user', None)
            session.pop('terms_accepted', None)
            return redirect('/login')

        if 'display_name' in request.form:
            session['user']['display_name'] = request.form['display_name']
            flash('Anzeigename erfolgreich geändert.')

    return render_template('settings.html', user=session['user'], storage_usage=user_storage_usage, storage_limit=storage_limit, storage_usage_percentage=storage_usage_percentage)

@app.route('/cloud/private/<file_name>')
def private_cloud(file_name):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    secure_file_name = secure_filename(file_name)
    return send_from_directory(init_cloud_folder(), secure_file_name)

@app.route('/cloud/private/<file_name>/download')
def download(file_name):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    secure_file_name = secure_filename(file_name)
    download_token = generate_unique_code()

    # Save token and filename mapping (You can use a database or a dictionary)
    session[download_token] = secure_file_name

    return redirect(url_for('download_info', file_name=secure_file_name, download_token=download_token))

@app.route('/cloud/private/<file_name>/<download_token>')
def download_info(file_name, download_token):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    secure_file_name = secure_filename(file_name)

    if session.get(download_token) != secure_file_name:
        return "Invalid download link", 403

    file_path = os.path.join(init_cloud_folder(), secure_file_name)
    file_size = os.path.getsize(file_path)
    user = session['user']

    return render_template('download_info.html', file_name=secure_file_name, download_token=download_token, file_size=file_size, user=user)

@app.route('/download/<download_token>')
def download_file(download_token):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    file_name = session.get(download_token)
    if not file_name:
        return "Invalid download link", 403

    return send_from_directory(init_cloud_folder(), file_name, as_attachment=True)

@app.route('/cloud/private/<file_name>/delete')
def delete(file_name):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    secure_file_name = secure_filename(file_name)

    recycle_bin_folder = os.path.join(init_cloud_folder(), '!_RECYCLE_BIN')
    if not os.path.exists(recycle_bin_folder):
        os.makedirs(recycle_bin_folder)

    if os.path.exists(os.path.join(init_cloud_folder(), secure_file_name)):
        os.remove(os.path.join(init_cloud_folder(), secure_file_name))
        return redirect('/')

    os.rename(os.path.join(init_cloud_folder(), secure_file_name), os.path.join(recycle_bin_folder, secure_file_name))

    return redirect('/')

@app.route('/terms', methods=['GET', 'POST'])
def terms():
    if request.method == 'POST':
        if 'terms_accepted' in request.form:
            session['terms_accepted'] = True
            return redirect(url_for('home'))
        else:
            flash('Bitte akzeptieren Sie die Nutzungsbedingungen.')

    return render_template('terms.html')

@app.route('/cloud/private/<file_name>/info')
def file_info(file_name):
    if not is_logged_in():
        return redirect('/login')

    if not check_terms_accepted():
        return redirect('/terms')

    secure_file_name = secure_filename(file_name)
    file_path = os.path.join(init_cloud_folder(), secure_file_name)

    if not os.path.exists(file_path):
        flash("Datei nicht gefunden.")
        return redirect('/')

    file_info = {
        'file_name': secure_file_name,
        'file_size': os.path.getsize(file_path),
        'upload_date': datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
        'user': session['user']['username']
    }

    return render_template('file_info.html', file_info=file_info)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
