/* Log out the main plattform account as well on a logout button click: */
document.addEventListener('DOMContentLoaded', function() {
    $('li[data-id="logout"] a').click(function(){
        var baseUrl = '<?php print_unescaped(\OC::$server->getConfig()->getSystemValue('wechange_plattform_root', '/')); ?>';
        $.ajax({
            url: baseUrl + '/logout/',
            async: false,
            xhrFields: {
                withCredentials: true
            }
        });
    });
    $('.info-nav-button').click(function(event){
        event.stopPropagation();
        event.preventDefault();
        OCP.Loader.loadScript('firstrunwizard', 'firstrunwizard.js').then(function () {
            OCA.FirstRunWizard.open(false);
            OC.hideMenus(function () {
                return false;
            });
        });
        return true;
    });            
});