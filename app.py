import os, uuid
from pathlib import Path
from urllib.parse import urlparse
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-development-secret')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
UPLOADS = BASE / 'static' / 'uploads'
UPLOADS.mkdir(parents=True, exist_ok=True)
STATUSES = ('Watching', 'Completed', 'Plan to Watch', 'On Hold', 'Dropped')
ALLOWED = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
SORTS = {'updated': 'updated_at DESC', 'title': 'title ASC', 'rating': 'rating DESC', 'progress': 'watched_episodes DESC'}

def db():
    return mysql.connector.connect(host=os.getenv('DB_HOST','127.0.0.1'), port=int(os.getenv('DB_PORT','3306')), user=os.getenv('DB_USER','root'), password=os.getenv('DB_PASSWORD',''), database=os.getenv('DB_NAME','anime_watchlist'), connection_timeout=5)

def parse_form():
    title=request.form.get('title','').strip(); genre=request.form.get('genre','').strip(); status=request.form.get('status','Plan to Watch').strip(); notes=request.form.get('notes','').strip(); poster_url=request.form.get('poster_url','').strip()
    if not title: raise ValueError('Anime title is required.')
    if len(title)>160 or len(genre)>120 or len(notes)>5000: raise ValueError('Please check the maximum field lengths.')
    if status not in STATUSES: raise ValueError('Select a valid viewing status.')
    if poster_url:
        u=urlparse(poster_url)
        if u.scheme not in ('http','https') or not u.netloc: raise ValueError('Poster URL must start with http:// or https://.')
    try:
        total=int(request.form.get('total_episodes') or 0); watched=int(request.form.get('watched_episodes') or 0)
        rating=float(request.form['rating']) if request.form.get('rating','').strip() else None
    except ValueError: raise ValueError('Episode counts and rating must be valid numbers.')
    if total<0 or watched<0 or (total and watched>total): raise ValueError('Episode counts must be non-negative and watched episodes cannot exceed the total.')
    if rating is not None and not 0<=rating<=10: raise ValueError('Rating must be between 0 and 10.')
    return dict(title=title,genre=genre,total=total,watched=watched,status=status,rating=rating,favorite=int(request.form.get('is_favorite')=='on'),notes=notes,poster_url=poster_url or None)

def save_poster(upload):
    if not upload or not upload.filename: return None
    safe=secure_filename(upload.filename)
    if '.' not in safe or safe.rsplit('.',1)[1].lower() not in ALLOWED: raise ValueError('Poster must be PNG, JPG, JPEG, WEBP or GIF.')
    ext=safe.rsplit('.',1)[1].lower(); name=f'{uuid.uuid4().hex}.{ext}'; upload.save(UPLOADS/name); return name

def remove_poster(name):
    if name:
        path=UPLOADS/Path(name).name
        try:
            if path.is_file(): path.unlink()
        except OSError: app.logger.warning('Unable to remove poster %s', name)

def get_anime(anime_id):
    conn=db()
    try:
        cur=conn.cursor(dictionary=True); cur.execute('SELECT * FROM anime WHERE id=%s',(anime_id,)); return cur.fetchone()
    finally: conn.close()

@app.errorhandler(413)
def too_large(_):
    flash('Upload is too large. Maximum request size is 5 MB.','error'); return redirect(url_for('index'))

@app.route('/')
def index():
    q=request.args.get('q','').strip(); status=request.args.get('status','').strip(); sort=request.args.get('sort','updated')
    if sort not in SORTS: sort='updated'
    clauses=[]; args=[]
    if q: clauses.append('(title LIKE %s OR genre LIKE %s)'); args.extend([f'%{q}%',f'%{q}%'])
    if status in STATUSES: clauses.append('status=%s'); args.append(status)
    sql='SELECT * FROM anime'+((' WHERE '+' AND '.join(clauses)) if clauses else '')+' ORDER BY '+SORTS[sort]
    conn=None
    try:
        conn=db(); cur=conn.cursor(dictionary=True); cur.execute(sql,tuple(args)); rows=cur.fetchall()
        cur.execute("SELECT COUNT(*) total, SUM(status='Watching') watching, SUM(status='Completed') completed, SUM(is_favorite=1) favorites FROM anime")
        stats=cur.fetchone() or {}
    except Error:
        app.logger.exception('Dashboard database error'); rows=[]; stats={}; flash('Database unavailable. Check MySQL and your .env settings.','error')
    finally:
        if conn and conn.is_connected(): conn.close()
    return render_template('index.html', anime_list=rows, stats=stats, statuses=STATUSES, search=q, selected_status=status, selected_sort=sort)

@app.route('/anime/new', methods=['GET','POST'])
def create_anime():
    if request.method=='POST':
        poster=None
        try:
            d=parse_form(); poster=save_poster(request.files.get('poster_file'))
            if poster: d['poster_url']=None
            conn=db()
            try:
                cur=conn.cursor(); cur.execute('''INSERT INTO anime(title,genre,total_episodes,watched_episodes,status,rating,is_favorite,notes,poster_filename,poster_url) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(d['title'],d['genre'],d['total'],d['watched'],d['status'],d['rating'],d['favorite'],d['notes'],poster,d['poster_url'])); conn.commit()
            finally: conn.close()
            flash('Anime added to your watchlist.','success'); return redirect(url_for('index'))
        except ValueError as e:
            remove_poster(poster); flash(str(e),'error')
        except Error:
            remove_poster(poster); app.logger.exception('Create database error'); flash('Could not save the anime. Check database settings.','error')
    return render_template('form.html', anime=None, statuses=STATUSES, page_title='Add Anime')

@app.route('/anime/<int:anime_id>/edit', methods=['GET','POST'])
def edit_anime(anime_id):
    try: anime=get_anime(anime_id)
    except Error:
        app.logger.exception('Edit lookup error'); flash('Could not load this anime.','error'); return redirect(url_for('index'))
    if not anime: abort(404)
    if request.method=='POST':
        new_poster=None
        try:
            d=parse_form(); new_poster=save_poster(request.files.get('poster_file'))
            poster=new_poster or anime.get('poster_filename')
            if new_poster: d['poster_url']=None
            conn=db()
            try:
                cur=conn.cursor(); cur.execute('''UPDATE anime SET title=%s,genre=%s,total_episodes=%s,watched_episodes=%s,status=%s,rating=%s,is_favorite=%s,notes=%s,poster_filename=%s,poster_url=%s WHERE id=%s''',(d['title'],d['genre'],d['total'],d['watched'],d['status'],d['rating'],d['favorite'],d['notes'],poster,d['poster_url'],anime_id)); conn.commit()
            finally: conn.close()
            if new_poster: remove_poster(anime.get('poster_filename'))
            flash('Anime details updated.','success'); return redirect(url_for('index'))
        except ValueError as e: remove_poster(new_poster); flash(str(e),'error')
        except Error: remove_poster(new_poster); app.logger.exception('Update database error'); flash('Could not update this anime.','error')
    return render_template('form.html', anime=anime, statuses=STATUSES, page_title='Edit Anime')

@app.route('/anime/<int:anime_id>/delete', methods=['POST'])
def delete_anime(anime_id):
    try:
        anime=get_anime(anime_id)
        if not anime: abort(404)
        conn=db()
        try:
            cur=conn.cursor(); cur.execute('DELETE FROM anime WHERE id=%s',(anime_id,)); conn.commit()
        finally: conn.close()
        remove_poster(anime.get('poster_filename')); flash('Anime deleted.','success')
    except Error: app.logger.exception('Delete database error'); flash('Could not delete this anime.','error')
    return redirect(url_for('index'))

@app.route('/anime/<int:anime_id>/progress', methods=['POST'])
def progress(anime_id):
    action=request.form.get('action')
    if action not in ('increase','decrease'): abort(400)
    conn=None
    try:
        conn=db(); cur=conn.cursor()
        cur.execute('SELECT id FROM anime WHERE id=%s',(anime_id,))
        if cur.fetchone() is None: abort(404)
        if action=='increase': cur.execute('UPDATE anime SET watched_episodes=LEAST(watched_episodes+1,IF(total_episodes>0,total_episodes,2147483647)) WHERE id=%s',(anime_id,))
        else: cur.execute('UPDATE anime SET watched_episodes=GREATEST(watched_episodes-1,0) WHERE id=%s',(anime_id,))
        conn.commit(); flash('Episode progress updated.','success')
    except Error: app.logger.exception('Progress update error'); flash('Could not update progress.','error')
    finally:
        if conn and conn.is_connected(): conn.close()
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename): return send_from_directory(UPLOADS,filename)

@app.route('/health')
def health():
    try: conn=db(); conn.close(); return {'status':'ok','database':'connected'},200
    except Error: return {'status':'error','database':'unavailable'},503

if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
