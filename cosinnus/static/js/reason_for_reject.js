$( document ).ready(function() {
    $('input[type=radio]').change(function() {
        var currentId = this.name.split('-')[1];
        if (this.value == "4") {
            $('#collapse' + currentId).collapse({toggle: false});
            $('#collapse' + currentId).collapse('hide');
        } else {
            $('#collapse' + currentId).collapse({toggle: false});
            $('#collapse' + currentId).collapse('show');
            
        }
    });
});