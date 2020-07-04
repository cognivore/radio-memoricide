from flask import Flask, render_template, request

from sanitize_filename import sanitize

import subprocess
import threading
import time

import pprint
import json
pp = pprint.PrettyPrinter(indent=4)
import os

app = Flask(__name__)

@app.route('/current', methods = ['POST'])
def current():
  if 'login' in request.form:
    mkkeepalive(request.form)
  p = subprocess.run(["mpc", "current"], stdout=subprocess.PIPE)
  return p.stdout.decode('utf-8').strip()

@app.route('/')
def query():
   return render_template('radio.html')

@app.route('/scrobble', methods = ['POST'])
def scrobble():
  if 'login' not in request.form:
    return "Please provide at least a login"
  if 'password' in request.form:
    mkconfig(request.form)
  pp.pprint(("Starting mpdas", "...was", get_pids()))
  pid = run_mpdas(request.form)
  pp.pprint(("Is", get_pids(), "...adding", pid))
  mkpid(request.form, pid)
  mkkeepalive(request.form)
  if (request.form['save'] == 'false'):
    os.remove(os.path.join(mpdas_dir(), sanitize(request.form['login'])))
  return "Thanks"

@app.route('/stop', methods = ['POST'])
def stop():
  if 'login' not in request.form:
    return "Please provide at least a login"
  pp.pprint(("Stopping mpdas", "...was", get_pids()))
  cleanup_do(kafile(request.form))
  pp.pprint(("Is", get_pids()))
  return "Thanks"

def mpdas_dir():
  return os.path.join('/', 'home', 'sweater', '.mpd', 'mpdas')

def conffile(form):
  return os.path.join(mpdas_dir(), sanitize(form['login']))

def suf():
  return '.keepalive'

def kafile(form):
  return '.' + sanitize(form['login']) + suf()

def katologin(kafname):
  return kafname[1:-len(suf())]

def katopid(kafname):
  return '.' + katologin(kafname) + '.pid'

def iskafile(fname):
  return fname[0] == '.' and fname[-1] == 'e'

def getpid(login):
  fpid = logintopidfname(sanitize(login))
  pp.pprint(("Checking if", fpid, "is file"))
  if not os.path.isfile(fpid):
    pp.pprint("Nope")
    return None
  fh = open(fpid)
  fc = fh.read()
  fh.close()
  return fc

def logintopidfname(login):
  return os.path.join(mpdas_dir(), '.' + sanitize(login) + '.pid')

def mkpid(form, pid):
  with open(os.path.join(mpdas_dir(), '.' + sanitize(form['login']) + '.pid'), 'w+') as fh:
    fh.write(pid)

def get_pids():
  p = subprocess.run(["pidof", "mpdas"], stdout=subprocess.PIPE)
  return p.stdout.decode('utf-8').strip().split(' ')

def run_mpdas(form):
  ps0 = get_pids()
  pid_maybe = getpid(sanitize(form['login']))
  pp.pprint(("Checking if", sanitize(form['login']), "is already served by", pid_maybe, "which is running. List:", ps0))
  if pid_maybe is not None:
    pp.pprint("Yes")
    return pid_maybe
  p = subprocess.run(["mpdas", "-d", "-c", conffile(form)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if p.stdout:
    pp.pprint(p.stdout.decode('utf-8')) # I hope it awaits lol
  if p.stderr:
    pp.pprint(p.stderr.decode('utf-8')) # I hope it awaits lol
  pid = next(x for x in get_pids() if x not in ps0) 
  pp.pprint(pid)
  return pid

def mkconfig(form):
  args = (sanitize(form['login']), form['password'])
  config = '''username = {0}
password = {1}
debug = 0'''.format(*args)
  with open(os.path.join(mpdas_dir(), sanitize(form['login'])), 'w+') as fh:
    fh.write(config)

def mkkeepalive(form):
  with open(os.path.join(mpdas_dir(), kafile(form)), 'w+') as fh:
    fh.write(str(time.time()))

def keepalive(form):
  if 'login' in form:
    mkkeepalive(form)

def cleanup_do(fname):
  pp.pprint(("Cleaning up", fname))
  os.remove(os.path.join(mpdas_dir(), fname))
  fpid = os.path.join(mpdas_dir(), katopid(fname))
  if os.path.isfile(fpid):
    fhpid = open(fpid)
    fcpid = fhpid.read()
    fhpid.close()
    pp.pprint(("Killing", fcpid))
    pp.pprint(("Was", get_pids()))
    p = subprocess.run(["kill", fcpid], stdout=subprocess.PIPE)
    p.stdout
    pp.pprint(("Is", get_pids()))
    os.remove(fpid)

def cleanup():
  if len(os.listdir(mpdas_dir())) < 1:
    return
  for fname in os.listdir(mpdas_dir()):
    if iskafile(fname):
      fh = open(os.path.join(mpdas_dir(), fname))
      t0 = fh.read()
      fh.close()
      t0 = float(t0)
      if time.time() - t0 > 66.666:
        cleanup_do(fname)

def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

if __name__ == '__main__':
  set_interval(cleanup, 1)
  app.run(host = '0.0.0.0', port = 5666, debug = False)
