$(document).ready(function() {
    $("#id_country").change(function() {
        $("#id_holiday").children('option').hide();
        $("#id_holiday").children("." + $(this).val()).show();
    });
})
