########################################################################################
#                                                                                      #
#   Author: Bertrand Neron,                                                            #
#   Organization:'Biological Software and Databases' Group, Institut Pasteur, Paris.   #
#   Distributed under GPLv2 Licence. Please refer to the COPYING.LIB document.         #
#                                                                                      #
########################################################################################

import sys
import os.path

import logging
p_log = logging.getLogger('Mobyle.Policy')


def queue(queueName):
    """
    @return: the name of the queue to be used to execute the job
    @rtype: string
    """
    return queueName


def emailCheck(**args):
    """
    check if the email according to the local rules.
    @return:
     - Mobyle.Net.EmailAddress.VALID    if the email is valid
     - Mobyle.Net.EmailAddress.INVALID  if the email is rejected
     - Mobyle.Net.EmailAddress.CONTINUE to continue futher the email validation process
    """
    import Mobyle.Net
    return Mobyle.Net.EmailAddress.CONTINUE


def emailUserMessage(method):
    messages = {
        'host': "you have abused our service. Your are not allowed to run on this server for now. For more informations contact mobyle@pasteur.fr",
        'syntax': "you are not allowed to run on this server for now",
        'blackList': "you have abused our service. Your are not allowed to run on this server for now. For more informations contact mobyle@pasteur.fr",
        'LocalRules': "you are not allowed to run on this server for now",
        'dns': "you are not allowed to run on this server for now",
    }
    try:
        return messages[method]
    except KeyError:
        return "you are not allowed to run on this server for now"


def authenticate(login, passwd):
    """
    Mobyle administrator can put authentification code here. this function must return either
     - Mobyle.AuthenticatedSession.AuthenticatedSession.CONTINUE:
                the method does not autentified this login/passwd. The fall back method must be applied.
     - Mobyle.AuthenticatedSession.AuthenticatedSession.VALID:
               the login/password has been authenticated.
     - Mobyle.AuthenticatedSession.AuthenticatedSession.REJECT:
              the login/password is not allow to continue.
    """
    import Mobyle.AuthenticatedSession

    return Mobyle.AuthenticatedSession.AuthenticatedSession.CONTINUE


def allow_to_be_executed(job):
    """
    check if the job is allowed to be executed
    if a job is not allowed must raise a UserError
    @param job: the job to check before to submit it to Execution
    @type job: L{Job} instance
    @raise UserValueError: if the job is not allowed to be executed
    """
    # place here the code you want to be executed to allow a job to be executed.
    # this is the last control be fore DRM submission
    # if you want to limit simultaneous job according some criteria as IP or user email, ...
    # this this the right place to put your code
    from Mobyle.MobyleError import UserValueError, MobyleError
    try:
        return over_limit(job)
    except UserValueError, err:
        raise UserValueError(parameter=None, msg=str(err))
    except Exception, err:
        p_log.error(str(err), exc_info=True)
        raise MobyleError, "Internal Server Error"


def over_limit(job):
    """
    check if the user (same email) has a similar job (same command line or same workflow name) running
    @param job: the job to check before to submit it to Execution
    @type job: L{Job} instance
    @raise UserValueError: if the number of similar jobs exceed the Config.SIMULTANEOUS_JOBS
    """
    from hashlib import md5
    import glob
    from Mobyle.Admin import Admin
    from Mobyle.MobyleError import UserValueError, MobyleError

    max_same_jobs = job.cfg.max_similar_job_per_user()
    max_user_jobs = job.cfg.max_job_per_user()

    user_email = str(job.getEmail())
    newMd5 = md5()
    newMd5.update(job.getCommandLine())
    newDigest = newMd5.hexdigest()

    work_dir = job.getDir()
    thisJobAdm = Admin(work_dir)
    thisJobAdm.setMd5(newDigest)
    thisJobAdm.commit()

    if thisJobAdm.getWorkflowID():
        # this job is a subtask of a workflow
        # we allow a workflow to run several identical job in parallel
        return True
    mask = os.path.normpath("%s/*.*" % (job.cfg.admindir()))
    jobs = glob.glob(mask)

    same_jobs_nb = 0
    jobs_nb = 0
    msg = None
    for one_job in jobs:
        try:
            oldAdm = Admin(one_job)
        except MobyleError, err:
            if os.path.lexists(one_job):
                p_log.critical("%s/%s: invalid job in ADMINDIR : %s" % (job.getServiceName(), job.getKey(), err))
            continue
        if (oldAdm.getWorkflowID()):
            # this job is NOT a workflow but
            # this job is the "same" than a workflow subtasks
            # we allow a workflow to run several identical job in parallel
            continue
        old_email = oldAdm.getEmail()
        oldDigest = oldAdm.getMd5()
        if user_email == old_email:
            oldStatus = job.getStatus()
            if oldStatus.isEnded():
                p_log.debug("oldStatus.isEnded() = True")
                continue
            jobs_nb += 1
            if max_user_jobs and jobs_nb >= max_user_jobs:
                msg = "%d jobs (%s) have been already submitted (md5 = %s)" % (jobs_nb,
                                                                               os.path.basename(one_job),
                                                                               newDigest
                                                                               )
                userMsg = " %d job(s) have been already submitted, and are(is) not finished yet. Please wait for the end of these jobs before you resubmit." % (
                jobs_nb)
                p_log.warning(msg + " : run aborted ")
                raise UserValueError(parameter=None, msg=userMsg)
            if newDigest == oldDigest:
                same_jobs_nb += 1
                if max_same_jobs and same_jobs_nb >= max_same_jobs:
                    msg = "%d similar jobs (%s) have been already submitted (md5 = %s)" % (
                        same_jobs_nb,
                        os.path.basename(one_job),
                        newDigest
                    )
                    userMsg = " %d similar job(s) have been already submitted, and are(is) not finished yet. Please wait for the end of these jobs before you resubmit." % (
                    same_jobs_nb)
                    p_log.warning(msg + " : run aborted ")
                    raise UserValueError(parameter=None, msg=userMsg)
    return True
