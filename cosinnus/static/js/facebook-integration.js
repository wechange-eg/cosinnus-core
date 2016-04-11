$(function() {
    
    $.cosinnus.facebookIntegration = {
            
        PERMISSIONS: 'publish_actions',
        APP_ID: '467240103473755',
        
        isLoaded: false,
        
        userLoggedIn: false,
        userHasPermissions: false,
        
        userID: ((typeof cosinnus_fb_userID !== 'undefined') ? cosinnus_fb_userID : null),
        //accessToken: null,
        
        
        // This function is called when someone finishes with the Login
        // Button.  See the onlogin handler attached to it in the sample
        // code below.
        checkLoginState: function(callbackSuccess, callbackFail) {
          FB.getLoginStatus(function(response) {
              if (response['status'] == 'connected') {
                  callbackSuccess();
              } else {
                  if (typeof callbackFail !== 'undefined') {
                      callbackFail();
                  }
              }
          });
        },
        
        checkPermissions: function(callbackSuccess, callbackFail) {
            if ($.cosinnus.facebookIntegration.userID) {
                FB.api( "/{0}/permissions".format($.cosinnus.facebookIntegration.userID),
                        function (response) {
                    
                    var failed = true;
                    console.log('result of check perms')
                    console.log(response)
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
                                console.log('breaking')
                                console.log(given)
                                break;
                            }
                        }
                    } 
                    if (!failed) {
                        console.log('Got all perms!');
                    } else {
                        console.log('failed')
                        if (typeof callbackFail !== 'undefined') {
                            callbackFail({status: 'not-logged-in'});
                        }
                    }
                    
                });
            } 
        },
        
        loadFacebookIntegration: function() {
            window.fbAsyncInit = function() {
                FB.init({
                  appId      : $.cosinnus.facebookIntegration.APP_ID,
                  cookie     : true,  // enable cookies to allow the server to access 
                                      // the session
                  xfbml      : false,  // parse social plugins on this page
                  version    : 'v2.5' // use graph api version 2.5
                });
    
                // Now that we've initialized the JavaScript SDK, we call 
                // FB.getLoginStatus().  This function gets the state of the
                // person visiting this page and can return one of three states to
                // the callback you provide.  They can be:
                //
                // 1. Logged into your app ('connected')
                // 2. Logged into Facebook, but not your app ('not_authorized')
                // 3. Not logged into Facebook and can't tell if they are logged into
                //    your app or not.
                //
                // These three cases are handled in the callback function.
    
                $.cosinnus.facebookIntegration.checkLoginState(function(){console.log('loggedin')}, function(){console.log('notloggedin')});
    
            };
            
            (function(d, s, id) {
                var js, fjs = d.getElementsByTagName(s)[0];
                if (d.getElementById(id)) return;
                js = d.createElement(s); js.id = id;
                js.src = "//connect.facebook.net/en_US/sdk.js";
                fjs.parentNode.insertBefore(js, fjs);
              }(document, 'script', 'facebook-jssdk'));
            
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
                        //$.cosinnus.facebookIntegration.accessToken = response.authResponse.accessToken;
                        $.cosinnus.facebookIntegration.userLoggedIn = true;
                        

                        // save widget configs to server
                        $.post( "/fb-integration/save-auth-tokens/", { authResponse: JSON.stringify(response.authResponse) }, "json")
                        .done(function( data ) {
                            if (typeof successCallback !== 'undefined') {
                                successCallback(data);
                            }
                        })
                        .fail(function(error) {
                            console.log('error saving credentials')
                            console.log(error)
                            alert('There was an error connecting your facebook account on our side! Please try to login again!')
                        });
                        
                        
                        
                    } else {
                        console.log('Login not successful');
                        console.log(response)
                    }
                    
                    
                }, {scope: $.cosinnus.facebookIntegration.PERMISSIONS});
            }
        },
        
    };
    
    
    $('#loadFacebookIntegrationButton').click(function(){
        $.cosinnus.facebookIntegration.loadFacebookIntegration();
        $(this).hide();
        $('#loginFacebookIntegrationButton').show();
    });
    
    $('#loginFacebookIntegrationButton').click(function(){
        $.cosinnus.facebookIntegration.doLogin(function(data){
            $('#loginFacebookIntegrationButton').hide();
            $('#facebookIntegrationPanel').show();
            $('.data-fb-username').text(data.username);
        });
    });
    
    if ($.cosinnus.facebookIntegration.userID) {
        $('#loadFacebookIntegrationButton').hide()
        $('#loginFacebookIntegrationButton').hide();
        $('#facebookIntegrationPanel').show();
    }
    
});

