$( document ).ready(function() {
    $('input[type=radio]').change(function() {
        if(this.value !== 4){
            var currentId = this.name.split('-')[1]
            $('#collapse' + currentId).collapse('show');
        }
    });
});