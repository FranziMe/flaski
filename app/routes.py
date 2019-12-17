from flask import render_template, Flask, Response, request, url_for, redirect, session, send_file, flash, jsonify
from app import app
from werkzeug.utils import secure_filename
from flask_session import Session
from app.forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from app.forms import RegistrationForm
from datetime import datetime
from app import db
from werkzeug.urls import url_parse


import os
import io
import sys
import random
import json

import matplotlib
matplotlib.use('agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import mpld3

import pandas as pd

import base64

sess = Session()
sess.init_app(app)

ALLOWED_EXTENSIONS=["xlsx","tsv","csv"]
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
def make_figure(df,pa):
    x=df[pa["xvals"]].tolist()
    y=df[pa["yvals"]].tolist()

    # MAIN FIGURE
    #fig = Figure()
    fig=plt.figure(figsize=(6,6))
    plt.scatter(x, y, \
        marker=pa["marker"], \
        s=int(pa["markers"]),\
        c=pa["markerc"])

    plt.title(pa['title'], fontsize=int(pa["titles"]))
    plt.xlabel(pa["xlabel"], fontsize=int(pa["xlabels"]))
    plt.ylabel(pa["ylabel"], fontsize=int(pa["ylabels"]))

    return fig

def figure_defaults():
    
    # https://matplotlib.org/3.1.1/api/markers_api.html
    # https://matplotlib.org/2.0.2/api/colors_api.html

    standard_sizes=[ str(i) for i in list(range(101)) ]

    # lists allways need to have thee default value after the list
    # eg.:
    # "title_size":standard_sizes,\
    # "titles":"20"

    plot_arguments={
        "title":'Scatter plot',\
        "title_size":standard_sizes,\
        "titles":"20",\
        "xcols":[],\
        "xvals":None,\
        "ycols":[],\
        "yvals":None,\
        "markerstyles":[".",",","o","v","^","<",">",\
            "1","2","3","4","8",\
            "s","p","*","h","H","+","x",\
            "X","D","d","|","_"],\
        "marker":".",\
        "marker_size":standard_sizes,\
        "markers":"50",\
        "marker_color":["blue","green","red","cyan","magenta","yellow","black","white"],\
        "markerc":"black",\
        "xlabel":"x",\
        "xlabel_size":standard_sizes,\
        "xlabels":"14",\
        "ylabel":"y",\
        "ylabel_size":standard_sizes,\
        "ylabels":"14",\
        "download_format":["png","pdf","svg"],\
        "downloadf":"pdf",\
        "downloadn":"scatterplot",\
        "session_downloadn":"MySession.scatter.plot",\
        "inputsessionfile":"Select file.."
    }
    # not update list
    notUpdateList=["inputsessionfile"]

    # lists without a default value on the arguments
    excluded_list=[]

    # lists with a default value on the arguments
    allargs=list(plot_arguments.keys())

    # dictionary of the type 
    # {"key_list_name":"key_default_value"} 
    # eg. {"marker_size":"markers"}
    lists={} 
    for i in range(len(allargs)):
        if type(plot_arguments[allargs[i]]) == type([]):
            if allargs[i] not in excluded_list:
                lists[allargs[i]]=allargs[i+1]

    return plot_arguments, lists, notUpdateList


@app.route('/user/<user>', defaults={'width': None, 'height': None})
@app.route('/user/<user>/<width>/<height>')
def user(user, width=None, height=None):
    if not width or not height:
        return """
        <script>
        (() => window.location.href = window.location.href +
        ['', window.innerWidth, window.innerHeight].join('/'))()
        </script>
        """
    return 'Hello %s (%s, %s)' %(user, width, height)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(firstname=form.firstname.data,\
                lastname=form.lastname.data,\
                email=form.email.data,\
                organization=form.organization.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """ 
    renders the plot on the fly.
    https://gist.github.com/illume/1f19a2cf9f26425b1761b63d9506331f
    """

    if request.method == 'POST':

        # READ SESSION FILE IF AVAILABLE 
        # AND OVERWRITE VARIABLES
        inputsessionfile = request.files["inputsessionfile"]
        if inputsessionfile:
            session_=json.load(inputsessionfile)
            for k in list(session_.keys()):
                session[k]=session_[k]
            plot_arguments=session["plot_arguments"]

        else:
            # SELECTION LISTS DO NOT GET UPDATED 
            lists=session["lists"]

            # USER INPUT/PLOT_ARGUMENTS GETS UPDATED TO THE LATEST INPUT
            # WITH THE EXCEPTION OF SELECTION LISTS
            plot_arguments = session["plot_arguments"]
            for a in list(plot_arguments.keys()):
                if ( a in list(request.form.keys()) ) & ( a not in list(lists.keys())+session["notUpdateList"] ):
                    plot_arguments[a]=request.form[a]

            # VALUES SELECTED FROM SELECTION LISTS 
            # GET UPDATED TO THE LATEST CHOICE
            for k in list(lists.keys()):
                if k in list(request.form.keys()):
                    plot_arguments[lists[k]]=request.form[k]

            # UPDATE SESSION VALUES
            session["plot_arguments"]=plot_arguments
        
        # IF THE CURRENT FILE IS DIFFERENT FROM 
        # THE FILE CURRENTLY IN MEMORY FOR THIS SESSION
        # THAN UPDATE THE SESSION FILE
        # READ INPUT FILE
        inputfile = request.files["inputfile"]
        if inputfile:
            filename = secure_filename(inputfile.filename)
            if allowed_file(inputfile.filename):
                session["filename"]=filename
                fileread = inputfile.read()
                extension=filename.rsplit('.', 1)[1].lower()
                if extension == "xlsx":
                    filestream=io.BytesIO(fileread)
                    df=pd.read_excel(filestream)
                elif extension == "csv":
                    df=pd.read_csv(fileread)
                elif extension == "tsv":
                    df=pd.read_csv(fileread,sep="\t")
                
                session["df"]=df.to_json()
                
                cols=df.columns.tolist()

                # IF THE USER HAS NOT YET CHOOSEN X AND Y VALUES THAN PLEASE SELECT
                if (session["plot_arguments"]["xvals"] not in cols) & (session["plot_arguments"]["yvals"] not in cols):

                    session["plot_arguments"]["xcols"]=cols
                    session["plot_arguments"]["xvals"]=cols[0]

                    session["plot_arguments"]["ycols"]=cols
                    session["plot_arguments"]["yvals"]=cols[1]
                
                    sometext="Please select which values should map to the x and y axes."
                    plot_arguments=session["plot_arguments"]
                    return render_template('index.html', filename=filename, sometext=sometext, **plot_arguments)
                
            else:
                # IF UPLOADED FILE DOES NOT CONTAIN A VALID EXTENSION PLEASE UPDATE
                error_message="You can can only upload files with the following extensions: 'xlsx', 'tsv', 'csv'. Please make sure the file '%s' \
                has the correct format and respective extension and try uploadling it again." %filename
                return render_template('index.html', filename="Select file..", error_message=error_message, **plot_arguments)
        
        # READ INPUT DATA FROM SESSION JSON
        df=pd.read_json(session["df"])

        # CALL FIGURE FUNCTION
        fig=make_figure(df,plot_arguments)

        # TRANSFORM FIGURE TO BYTES AND BASE64 STRING
        figfile = io.BytesIO()
        plt.savefig(figfile, format='png')
        plt.close()
        figfile.seek(0)  # rewind to beginning of file
        figure_url = base64.b64encode(figfile.getvalue()).decode('utf-8')

        # MAKE SURE WE HAVE THE LATEST ARGUMENTS FOR THIS SESSION
        filename=session["filename"]
        plot_arguments=session["plot_arguments"]
        return render_template('index.html',  figure_url=figure_url, filename=filename, **plot_arguments)

    else:
        #sometext="get"

        # INITIATE SESSION
        session["filename"]="Select file.."

        plot_arguments, lists, notUpdateList=figure_defaults()

        session["plot_arguments"]=plot_arguments
        session["lists"]=lists
        session["notUpdateList"]=notUpdateList

        return render_template('index.html',  filename=session["filename"], **plot_arguments)

@app.route('/figure', methods=['GET','POST'])
@login_required
def figure():
    # READ INPUT DATA FROM SESSION JSON
    df=pd.read_json(session["df"])

    plot_arguments=session["plot_arguments"]

    # CALL FIGURE FUNCTION
    fig=make_figure(df,plot_arguments)

    #flash('Figure is being sent to download but will not be updated on your screen.')
    figfile = io.BytesIO()
    mimetypes={"png":'image/png',"pdf":"application/pdf","svg":"image/svg+xml"}
    plt.savefig(figfile, format=plot_arguments["downloadf"])
    plt.close()
    figfile.seek(0)  # rewind to beginning of file
    return send_file(figfile, mimetype=mimetypes[plot_arguments["downloadf"]], as_attachment=True, attachment_filename=plot_arguments["downloadn"]+"."+plot_arguments["downloadf"] )

@app.route('/downloadsession', methods=['GET','POST'])
@login_required
def downloadsession():
    # READ INPUT DATA FROM SESSION JSON
    session_={}
    for k in list(session.keys()):
        if k not in ['_permanent','fileread','_flashes']:
            session_[k]=session[k]

    session_file = io.BytesIO()
    session_file.write(json.dumps(session_).encode())
    session_file.seek(0)

    plot_arguments=session["plot_arguments"]
    return send_file(session_file, mimetype='application/json', as_attachment=True, attachment_filename=plot_arguments["session_downloadn"]+".json" )


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()