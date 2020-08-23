# * fixed bug

# * python 3.x
# *limitation, one-one server in sequence. skip step will invoke undefined global varible error
    #*fixed by stop using Global content, retrieve from email folder every time
# *bug: second line start with a, the. *fixed by recovering \r\n\r\n with double space
# *bug: auto retrieve email every 30mins even with no new email Prabably caused by Gmail server. *fixed by adding if UNSEEN is found
#     https://tools.ietf.org/html/rfc2177.html re-issue idle at least 29 mins to avoid being logged off
# *bug: wordcount_removed=0, float division by zero text tracback. *fixed with try except
# *bug: Thunder bird ' \r\n' cause ugly paragraph *fixed with updated ini_text function
# *bug: can not render ' sign *fixed by get_payload(decoe=True) to utf-8
# bug-suspect: uidlist[0] type None, try to pinpoint
# bug threading error and try/except block ineffective
#     http://stackoverflow.com/questions/16622132/imaplib2-imap-gmail-com-handler-bye-response-system-error
# bug exception will not run if error happens inside of idler change self.M to self.mail hoping consistence will help - no it didn't
      # instead of letting Gmail to do 29min break, I will manually ask to restart idler every 29min. I suspect Gmails rule is not constant


import imaplib2, time, email, base64
import smtplib
import re
import difflib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import *

def readme():
    """
    About AP(alpha 0.7):
        AP is a program to help folks to practice the article usage in English. With AP, you will be able to do 'fill in articles' practice on your own, with your chosen text.

    How to use:

        1. Create an assignment to practice
            + copy a paragraph or multi-paragraph of text from a website of well written English
            + paste as plain text (to eliminate embeded links etc.) to a blank email (no sigiture)
            + put email SUBJECT as "ap: my topic" ("" not included). you can put whatever topic after ap:
            + email to article.practice@gmail.com
            + you will receive your assignment email within 3 sec

        2. Do your assignment
            + click 'reply' on the received assignment
            + directly fill in articles in the original attached text (you may need to "expand" to see the text in some email client)
            + delete text content(recieved email info) before your assignment text.
                  PS: you can skip this step if you are using Gmail-webpage, Apple mail, Thunderbird.
            + click send

        3. Receive your marked assignment
            + you will receive the marked assignment within 3 sec
            + happy APing

    Plese send email with subject: "bug report" to report any bugs or suggestions by sending email with the subject: bug report

    """
    #print readme.__doc__


#Parse body text of email MIME string
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload(decode=True)
    elif maintype == 'text':
        return email_message_instance.get_payload(decode=True)

def ini_text(text):
    text_space = text.replace(' \r\n',' ').replace('\r\n',' ')
    return re.sub('\s\s+','\r\n\r\n',text_space).strip()

def markup(list_str):
    for i in range(0, len(list_str)):
        if ('- ' in list_str[i]):
            list_str[i] = '[Add' + list_str[i] + ']'
            list_str[i]=list_str[i].replace('- ','->')
        elif ('+ ' in list_str[i]):
            list_str[i] = '[Delete' + list_str[i] + ']'
            list_str[i]=list_str[i].replace('+ ','->')
        else:
            list_str[i]=list_str[i].replace(' ','') # use strip() will remove \n
        list_str_new = list_str
    return list_str_new

def make_comment(mark_num):
    if -10000<mark_num < 10:
        comment = 'Disaster!'
    if 10<= mark_num < 30:
        comment = 'Seriously? '
    if 30<= mark_num < 50:
        comment = 'Well... this is embarrassing.'
    if 50<= mark_num < 70:
        comment = 'Not too bad!'
    if 70<= mark_num < 80:
        comment = 'Pretty good!'
    if 80<= mark_num < 90:
        comment = 'Great job!'
    if 90<= mark_num < 100:
        comment = 'Fantastic!'
    if mark_num == 100:
        comment = 'King of articles!'
    return comment

# Define a idler https://gist.github.com/jexhson/3496039
# This is the threading object that does all the waiting on the event
class Idler(object):
    def __init__(self, conn):
        self.thread = Thread(target=self.idle)
        self.mail = conn
        self.event = Event()

    def start(self):
        self.thread.start()

    def stop(self):
        # This is a neat trick to make thread end. Took me a
        # while to figure that one out!
        self.event.set()

    def join(self):
        self.thread.join()

    def idle(self):
        # Starting an unending loop here
        while True:
            print(time.strftime("%c"),'AP listening...')
            # This is part of the trick to make the loop stop
            # when the stop() command is given
            if self.event.isSet():
                return
            self.needsync = False
            # A callback method that gets called when a new
            # email arrives. Very basic, but that's good.
            def callback(args):
                if not self.event.isSet():
                    self.needsync = True
                    self.event.set()
            # Do the actual idle call. This returns immediately,
            # since it's asynchronous.
            self.mail.idle(callback=callback)
            # This waits until the event is set. The event is
            # set by the callback, when the server 'answers'
            # the idle call and the callback function gets
            # called.
            self.event.wait()
            # Because the function sets the needsync variable,
            # this helps escape the loop without doing
            # anything if the stop() is called. Kinda neat
            # solution.
            if self.needsync:
                self.event.clear()
                self.dosync()

    # The method that gets called when a new email arrives.
    # Replace it with something better.
    def dosync(self):
        try:
            # check if the new email by trigger or auto-get email is UNSEEN
            status1, uidlist = mail.uid('search', None, 'UNSEEN')
            if uidlist[0]=='':
                print('Checked by Gmail every 29 mins just to keep M.Idler() alive...')
                return None
            elif uidlist[0]==None:
                print('uidlist[0] is None!!!! do nothing')
                return None
            else:
                ################
                # read request #
                ################
                latest_email_uid = uidlist[0].split()[-1]
                status2, uidlist1 = mail.uid('fetch', latest_email_uid, '(RFC822)')
                raw_email = uidlist1[0][1]
                email_message = email.message_from_string(raw_email)
                client_addr = email_message['From']
                client_subject = email_message['Subject']

                if 'ap: ' in client_subject:
                    # begin: remove article and send back to client#######################
                    content_old = ini_text(get_first_text_block(email_message))
                    # print information of interest
                    print('From:',client_addr)
                    print('Subject:',client_subject, '\n')
                    print(content_old) # original text content
                    # remove article
                    # split, keep \n \r
                    content = content_old.replace('\r\n',' Place_Holder[carriage_return]_So_Unique ')
                    content = content.replace('\n',' Place_Holder[newline]_So_Unique ')
                    text = content.split()

                    wordcount_before = len(text)
                    # protect exceptions from being removed
                    for i in range(1,len(text)):                                  # start from the 2nd element
                        if (text[i] == 'lot' or
                            text[i] == 'few' or
                            text[i] == 'little' or
                            text[i] == 'bit'):
                            text[i-1]=text[i-1]+('Place_Holder[keyword]_So_Unique')

                    # article remove function
                    def remove_word(the_list, val):
                        while val in the_list:
                            the_list.remove(val)

                    remove_word(text, 'a')
                    remove_word(text, 'A')
                    remove_word(text, 'an')
                    remove_word(text, 'An')
                    remove_word(text, 'the')
                    remove_word(text, 'The')

                    wordcount_after = len(text)

                    wordcount_removed = wordcount_before - wordcount_after

                    # recover exceptions
                    text = [elem.replace('Place_Holder[keyword]_So_Unique','') for elem in text]
                    text = [elem.replace('Place_Holder[newline]_So_Unique','\n') for elem in text]
                    text = [elem.replace('Place_Holder[carriage_return]_So_Unique','\r\n') for elem in text]

                    no_artical=' '.join(text)
                    no_artical=no_artical.replace(' \n \n ','\n\n')
                    no_artical=no_artical.replace(' \r\n','\r\n')
                    content_no_a=no_artical.replace('\r\n ','\r\n')

                    print('\n**',wordcount_removed,'words removed**')
                    print(content_no_a)

                    # send to client
                    msg = MIMEMultipart()
                    msg['From'] = 'article.practice@gmail.com'
                    msg['To'] = client_addr
                    msg['Subject'] = 'Assignment: '+client_subject.replace('ap:','').strip()+'_'+str(wordcount_removed)
                    msg.attach(MIMEText(content_no_a, 'plain'))

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(user_id, passward)
                    server.sendmail('article.practice@gmail.com', client_addr, msg.as_string())
                    server.quit()

                    # END: remove article and send back to client#######################

                elif 'Re: Assignment:' in client_subject:
                    # fetch submitted assignemnt
                    content = get_first_text_block(email_message)
                    content_submit = ini_text(re.sub('.+\s+.+wrote:','',content).replace("> ","").replace(">","")) # delete all above reply line

                    # directly fetch original text from sent mail folders
                    topic = re.findall('Re: Assignment: (.+)_',client_subject)[0]
                    wordcount_removed =int(re.findall('_(.+)',client_subject)[0])
                    mail.select('INBOX')
                    status1, data = mail.uid('search', None, '(SUBJECT "ap: %s")'%topic) # search and return uids instead
                    latest_email_uid = data[0].split()[-1]
                    status2, data1 = mail.uid('fetch', latest_email_uid, '(RFC822)')
                    raw_email = data1[0][1]
                    email_message = email.message_from_string(raw_email)
                    content_old = get_first_text_block(email_message).strip()

                    # Start: marking and send marked to client##############################
                    # marking

                    #convert \r\n to whitespace to accomodate a/the at the beginning of a line
                    text1=content_old.replace('\r\n',' ').split(' ')
                    text2=content_submit.replace('\r\n',' ').split(' ')

                    dif = list(difflib.Differ().compare(text1, text2))
                    dif1 = markup(dif)

                    content_marked=' '.join(dif1).replace('  ','\r\n\r\n')

                    mark_lost = content_marked.count('->')-content_marked.count('] [')

                    print(mark_lost)
                    try:
                        mark_num = round(100.*float(wordcount_removed - mark_lost)/float(wordcount_removed),1)
                    except: mark_num =0.0
                    try: comment = make_comment(mark_num)
                    except: comment = None

                    mark_final_str = 'Mark: %s%%' %mark_num +'\n'+comment

                    #sending
                    msg = MIMEMultipart()
                    msg['From'] = 'article.practice@gmail.com'
                    msg['To'] = client_addr
                    msg['Subject'] = 'Mark report: '+client_subject

                    mark_report = mark_final_str+'\n\n'+content_marked

                    print('\n',mark_report)

                    msg.attach(MIMEText(mark_report, 'plain'))

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(user_id, passward)

                    server.sendmail('article.practice@gmail.com', client_addr, msg.as_string())
                    server.quit()
# functional reply ############################################################################################
                    # End: marking and send marked to client###################
                elif client_subject.strip() in ['help','Help','HELP']:
                    print('\n'+client_subject.strip()+'requested')
                    # send instruction
                    msg = MIMEMultipart()
                    msg['From'] = 'article.practice@gmail.com'
                    msg['To'] = client_addr
                    msg['Subject'] = client_subject+':'+'How to use Article Practice(AP)'

                    msg.attach(MIMEText(readme.__doc__, 'plain'))

                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(user_id, passward)

                    server.sendmail('article.practice@gmail.com', client_addr, msg.as_string())
                    server.quit()
                    print('help info sent\n')

                elif client_subject.strip() in ['bug report', 'Bug Report', 'BUG REPORT']:
                    # move email from INBOX to Bug Report folder
                    latest_email_uid = uidlist[0].split()[-1]
                    result = mail.uid('COPY', latest_email_uid, 'Bug Report')

                    if result[0] == 'OK':
                        mov, data = mail.uid('STORE', latest_email_uid , '+FLAGS', '(\Deleted)')
                        mail.expunge()
                    print('\n*bug report recieved*, time.strftime("%c")\nmoved to Bug Report folder\n')

                else:
                    print('non-targeted email received from %s, \nSubject: %s \n *message ignored*.' %(client_addr,client_subject))
                    pass

        except:
                print('**',time.strftime("%c"),'Error occured INSIDE of Idler!**')
                pass
###################
# start listening #
###################
# use Superinterupt to stop loop  Win: ctrl+break  Mac ctrl+z
while True:
    online_time = 2*60*60
    try:
        print('Restarting AP...')
        # Set the following two lines to your creds and server
        mail = imaplib2.IMAP4_SSL("imap.gmail.com", 993)
        user_id = 'article.practice'
        passward = 'passarticle'
        #mail.list() # Out: list of "folders" aka labels in gmail.

        mail.login(user_id, passward)
        # We need to get out of the AUTH state, so we just select
        # the INBOX.
        mail.select("INBOX")

        # Start the Idler thread
        idler = Idler(mail)
        idler.start()
        # online time second

        time.sleep(online_time)

    except:
        print('**',time.strftime("%c"),'** Error OUTSIDE of idler() **')
        pass

    finally:
        print('**',time.strftime("%c"),'** restart every %s mins **' %online_time)
        # have to re Assign a thread to avoid try-except running at different threads
        # Clean up.
        idler.stop()
        idler.join()
        mail.close()
        # This is important!
        mail.logout()
        print('AP program terminated.\n\n')