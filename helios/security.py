"""
Helios Security -- mostly access control

Ben Adida (ben@adida.net)
"""

import urllib
# nicely update the wrapper function
from functools import update_wrapper

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext as _

from helios_auth.security import get_user
from models import Voter, Trustee, Election

import helios

class HSTSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        if settings.STS:
          response['Strict-Transport-Security'] = "max-age=31536000; includeSubDomains; preload"
        return response

# current voter
def get_voter(request, user, election):
  """
  return the current voter
  """
  voter = None
  if request.session.has_key('CURRENT_VOTER_ID'):
    voter = Voter.objects.get(id=request.session['CURRENT_VOTER_ID'])
    if voter.election != election:
      voter = None

  if not voter:
    if user:
      voter = Voter.get_by_election_and_user(election, user)

  return voter

# a function to check if the current user is a trustee
HELIOS_TRUSTEE_UUID = 'helios_trustee_uuid'
def get_logged_in_trustee(request):
  if request.session.has_key(HELIOS_TRUSTEE_UUID):
    return Trustee.get_by_uuid(request.session[HELIOS_TRUSTEE_UUID])
  else:
    return None

def set_logged_in_trustee(request, trustee):
  request.session[HELIOS_TRUSTEE_UUID] = trustee.uuid

#
# some common election checks
#
def do_election_checks(election, props):
  # frozen
  if props.has_key('frozen'):
    frozen = props['frozen']
  else:
    frozen = None
  
  # newvoters (open for registration)
  if props.has_key('newvoters'):
    newvoters = props['newvoters']
  else:
    newvoters = None
  
  # frozen check
  if frozen != None:
    if frozen and not election.frozen_at:
      raise PermissionDenied()
    if not frozen and election.frozen_at:
      raise PermissionDenied()
    
  # open for new voters check
  if newvoters != None:
    if election.can_add_voters() != newvoters:
      raise PermissionDenied()

  
def get_election_by_uuid(uuid):
  if not uuid:
    raise Exception(_("no election ID"))
      
  return Election.get_by_uuid(uuid)
  
# decorator for views that pertain to an election
# takes parameters:
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_view(**checks):
  
  def election_view_decorator(func):
    def election_view_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      if not election:
        raise Http404

      # do checks
      do_election_checks(election, checks)

      # if private election, only logged in voters
      if election.private_p and not checks.get('allow_logins',False):
        from views import password_voter_login
        if not user_can_see_election(request, election):
          return_url = request.get_full_path()
          return HttpResponseRedirect("%s?%s" % (reverse(password_voter_login, args=[election.uuid]), urllib.urlencode({
                  'return_url' : return_url
                  })))
    
      return func(request, election, *args, **kw)

    return update_wrapper(election_view_wrapper, func)
    
  return election_view_decorator

def user_can_admin_election(user, election):
  if not user:
    return False

  return election.admin == user and user.admin_p
  
def user_can_see_election(request, election):
  user = get_user(request)

  if not election.private_p:
    return True

  # election is private
  
  # but maybe this user is the administrator?
  if user_can_admin_election(user, election):
    return True

  # or maybe this is a trustee of the election?
  trustee = get_logged_in_trustee(request)
  if trustee and trustee.election.uuid == election.uuid:
    return True

  voter = get_voter(request, user, election)

  if user and not voter:
    if user.user_type in settings.AUTH_BIND_USERID_TO_VOTERID:
      voter = Voter.get_by_election_and_voter_id(election, user.user_id)
  # then this user has to be a voter
  return (voter != None)

def api_client_can_admin_election(api_client, election):
  return election.api_client == api_client and api_client != None
  
# decorator for checking election admin access, and some properties of the election
# frozen - is the election frozen
# newvoters - does the election accept new voters
def election_admin(**checks):
  
  def election_admin_decorator(func):
    def election_admin_wrapper(request, election_uuid=None, *args, **kw):
      election = get_election_by_uuid(election_uuid)

      user = get_user(request)
      if not user_can_admin_election(user, election):
        raise PermissionDenied()

      # do checks
      do_election_checks(election, checks)
        
      return func(request, election, *args, **kw)

    return update_wrapper(election_admin_wrapper, func)
    
  return election_admin_decorator
  
def trustee_check(func):
  def trustee_check_wrapper(request, election_uuid, trustee_uuid, *args, **kwargs):
    election = get_election_by_uuid(election_uuid)
    
    trustee = Trustee.get_by_election_and_uuid(election, trustee_uuid)
    
    if trustee == get_logged_in_trustee(request):
      return func(request, election, trustee, *args, **kwargs)
    else:
      raise PermissionDenied()
  
  return update_wrapper(trustee_check_wrapper, func)

def can_create_election(request):
  user = get_user(request)
  if not user:
	  return False

  if helios.ADMIN_ONLY:
    return user.admin_p
  else:
    return user.can_create_election()
  
def user_can_feature_election(user, election):
  if not user:
    return False

  if settings.FEATURE_ELECTION and user.admin_p:
    return True

  return False
