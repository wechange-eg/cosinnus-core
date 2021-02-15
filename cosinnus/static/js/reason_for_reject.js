$( document ).ready(function() {
    $('input[type=radio]').change(function() {
        var currentId = this.name.split('-')[1];
        if (this.value == "4") {
            $('#collapse-rejection-reason-' + currentId).collapse({toggle: false});
            $('#collapse-rejection-reason-' + currentId).collapse('hide');
        } else {
            $('#collapse-rejection-reason-' + currentId).collapse({toggle: false});
            $('#collapse-rejection-reason-' + currentId).collapse('show');
            
        }
    });
    
    $('.collapse-unedited-applications').on('click', function(){
        $('.collapse-application-details').each(function(){
             var me = $(this);
             var parentApplication = me.parent('.application');
             if (parentApplication.find('input[type="radio"]:checked').length > 0) {
                 me.collapse({toggle: false});
                 me.collapse('hide');
                 parentApplication.find('.application-toggle-button').addClass('collapsed');
             }
        });
    });
});