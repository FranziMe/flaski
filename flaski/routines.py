import pandas as pd


def reset_all(session):
    MINIMAL=['_permanent', '_fresh', 'csrf_token', 'user_id', '_id', 'PRIVATE_APPS']
    for k in list(session.keys()):
        if k not in MINIMAL:
            del(session[k])

def check_session_app(session,app):
    if "app" not in list(session.keys()):
        return None
    elif session["app"] == app :
        return None
    else:
        message="Your '%s' session has been reset."  %(session["app"])
            #Flaski is not yet made for working with multiple Apps nor data simultaneously on one single browser. \
            #If you wish to use multiple Apps or data simultaneously please use one App/data per web browser eg. Safari + Chrome. \
            #Your %s session has been reset."
        reset_all(session)
        return message

def session_to_file(session,file_type):
    session_={}
    for k in list(session.keys()):
        if k not in ['_permanent','fileread','_flashes',"width","height","csrf_token","user_id","_fresh","available_disk_space","_id","private_apps"]:
            session_[k]=session[k]
    if file_type=="ses":
        session_["ftype"]="session"
    elif file_type=="arg":
        if session_["app"] == "david":
            for k in ["ids","ids_bg"]:
                del(session_["plot_arguments"][k])
            for k in ["david_df","report_stats"]:
                del(session_[k])
        session_["ftype"]="arguments"
        del(session_["df"])
    return session_

def read_private_apps(useremail,app):
    PRIVATE_APPS=[]
    if app.config['PRIVATE_APPS']:
        df=pd.read_csv(app.config['PRIVATE_APPS'],index_col="app",sep="\t")
        df=df.transpose()
        dic=df.to_dict()
        for entry in list(dic.keys()):
            private_app=dic[entry]
            allowed=private_app["allowed"].split(",")
            if "all" in allowed:
                del(private_app["allowed"])
                PRIVATE_APPS.append(private_app)
            elif useremail in allowed:
                del(private_app["allowed"])
                PRIVATE_APPS.append(private_app)
            elif len([ s for s in allowed if s[0] == "#" ]) > 0 :
                for domain in [ s for s in allowed if s[0] == "#" ]:
                    if domain[1:] in useremail:
                        del(private_app["allowed"])
                        PRIVATE_APPS.append(private_app)
                        break
    return PRIVATE_APPS
