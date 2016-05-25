$(function() {
    
    $.cosinnus.facebookIntegration = {
            
        PERMISSIONS: 'publish_actions,publish_pages,manage_pages',
        APP_ID: COSINNUS_FACEBOOK_INTEGRATION_APP_ID,
        
        isLoaded: false,
        
        userLoggedIn: false,
        userHasPermissions: false,
        
        userID: ((typeof cosinnus_fb_userID !== 'undefined') ? cosinnus_fb_userID : null),
        
        checkPermissions: function(callbackSuccess, callbackFail) {
            /** Asynchronously check through the Facebook API if the user still has granted all permissions
             *  we require of them.
             *  Calls param callbackSuccess if yes, otherwise calls callbackFail */
            
            if ($.cosinnus.facebookIntegration.userID) {
                FB.api( "/{0}/permissions".format($.cosinnus.facebookIntegration.userID),
                        function (response) {
                    
                    var failed = true;
                    if (response && !response.error) {
                        /* handle the result */
                        failed = false;
                        var perms = $.cosinnus.facebookIntegration.PERMISSIONS.split(',');
                        for (perm in perms) {
                            var perm_found = false;
                            for (given in response.data) {
                                if (response.data[given].status == 'granted' && response.data[given].permission == perms[perm]) {
                                    perm_found = true;
                                }
                            }
                            if (!perm_found) {
                                failed = true;
                                break;
                            }
                        }
                    } 
                    if (!failed) {
                        if (typeof callbackSuccess !== 'undefined') {
                            callbackSuccess();
                        }
                    } else {
                        if (typeof callbackFail !== 'undefined') {
                            callbackFail({status: 'not-logged-in'});
                        }
                    }
                    
                });
            } 
        },
        
        loadFacebookIntegration: function(doneCallback) {
            // if already loaded, do not load twice, just call the callback and return
            if ($.cosinnus.facebookIntegration.isLoaded) {
                if (typeof doneCallback !== 'undefined') {
                    doneCallback();
                }
                return;
            }
            
            /** Facebook internal loading scripts begin ****************************** */
            window.fbAsyncInit = function() {
                FB.init({
                  appId      : $.cosinnus.facebookIntegration.APP_ID,
                  cookie     : true,  // enable cookies to allow the server to access 
                                      // the session
                  xfbml      : false,  // parse social plugins on this page
                  version    : 'v2.5' // use graph api version 2.5
                });
                if (typeof doneCallback !== 'undefined') {
                    doneCallback();
                }
            };
            (function(d, s, id) {
                var js, fjs = d.getElementsByTagName(s)[0];
                if (d.getElementById(id)) return;
                js = d.createElement(s); js.id = id;
                js.src = "//connect.facebook.net/en_US/sdk.js";
                fjs.parentNode.insertBefore(js, fjs);
              }(document, 'script', 'facebook-jssdk'));
            /** Facebook internal loading scripts end ****************************** */
            
            $.cosinnus.facebookIntegration.isLoaded = true;
        },
        
        doLogin: function(successCallback) {
            if (typeof FB.login === 'undefined') {
                alert('It seems you have installed an Addon that is blocking you from accessing the Facebook login. Please disable addons such as Ghostery to continue!');
            } else {
                FB.login(function(response) {
                    /*
                     * Response object:
                     * 
                     * 1) {status: "not_authorized", authResponse: null} // the user is either not logged into Facebook or explicitelly logged out of your application
                     * 2) {status: "unknown", authResponse: null} // the user is logged into Facebook but has not authenticated your application
                     * 3) {
                            status: 'connected',
                            authResponse: {
                                accessToken: '...',
                                expiresIn:'...',
                                signedRequest:'...',
                                userID:'...'
                            }
                        }  //the user is logged into Facebook and has authenticated your application
                     */
                    if (response.status == 'connected') {
                        $.cosinnus.facebookIntegration.userID = response.authResponse.userID;
                        $.cosinnus.facebookIntegration.userLoggedIn = true;

                        // save widget configs to server
                        $.post( "/fb-integration/save-auth-tokens/", { authResponse: JSON.stringify(response.authResponse) }, "json")
                        .done(function( data ) {
                            if (typeof successCallback !== 'undefined') {
                                successCallback(data);
                            }
                        })
                        .fail(function(error) {
                            // error saving credentials
                            alert('There was an error connecting your facebook account on our side! Please try to login again or contact an administrator!')
                        });
                    } else {
                        // fail silently when response came back but account wasn't connected
                        // the user probably didn't accept some permission, so they know what's up
                    }
                    
                }, {scope: $.cosinnus.facebookIntegration.PERMISSIONS}); // require these Facebook permissions from the user
            }
        },
        
    };
    
    
    $('#loadFacebookIntegrationButton').click(function(){
        $('#loadFacebookIntegrationButton').hide();
        $('.facebook-loading-spinner').show();
        $.cosinnus.facebookIntegration.loadFacebookIntegration(function (){
            // on completely loaded:
            $('#facebook-login-modal').modal('show');
            $('#loginFacebookIntegrationButton').removeAttr('disabled').css('opacity', '1.0');
            
            $('#loadFacebookIntegrationButton').show();
            $('.facebook-loading-spinner').hide();
        });
    });
    
    $('#loginFacebookIntegrationButton').click(function(){
        $('#loginFacebookIntegrationButton').attr('disabled', 'true').css('opacity', '0.6');
        $.cosinnus.facebookIntegration.doLogin(function(data){
            // on successful login:
            $('#loadFacebookIntegrationButton').hide();
            $('#facebook-login-modal').modal('hide');
            $('#facebookIntegrationPanel').show();
            $('.title-fb-username').attr('title', data.username);
            $('.src-fb-avatar').attr('src', data.avatar);
        });
    });
    
    if ($.cosinnus.facebookIntegration.userID) {
        $('#loadFacebookIntegrationButton').hide()
        $('#facebookIntegrationPanel').show();
    }
    
    // force disabling the post-to-facebook checkbox, that firefox will sometimes "remember" as checked
    $('#facebookIntegrationPostCheckbox').attr('checked', false);
    $('#facebookIntegrationPostGroupCheckbox').attr('checked', false);
});

