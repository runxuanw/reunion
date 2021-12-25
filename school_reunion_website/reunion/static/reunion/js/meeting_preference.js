$(document).ready(function() {

    var attending_dates = new Tagify(
        document.querySelector("input[id='id_selected_attending_dates']"),
        {
            userInput: false
        });
    $("#id_holiday").change(function() {
        attending_dates.addTags(
            [`${$("#id_holiday option:selected").attr('class')}:${$("#id_holiday option:selected").text()}`]);
    });
    $('input[id="id_custom_dates"]').daterangepicker({autoApply: true});
    $('input[id="id_custom_dates"]').on('apply.daterangepicker', function(ev, picker) {
        var repeat_option = $('input[name="repeat_option_for_adding_custom_dates"]:checked').val();
        if (repeat_option === undefined) {
            repeat_option = 'no_repeat';
        }
        attending_dates.addTags([`${$(this).val()}:${repeat_option}`]);
    });

    var weighted_attendants = new Tagify(
        document.querySelector("input[id='id_weighted_attendants']"),
        {
            userInput: false
        });
    function addWeightedAttendant(event) {
        var keycode = (event.keyCode ? event.keyCode : event.which);
        var name = $('#id_other_attendant').val();
        var weight = $('#id_other_attendant_weight').val();
        if(keycode == '13'){
            if (!name || !weight) {
                alert('Attendant Name and Attendant Value must both be set!');
                return;
            }
            weighted_attendants.addTags([`${name}:${weight}`]);
        }
    }
    $('#id_other_attendant').keypress(function(event){
        addWeightedAttendant(event);
    });
    $('#id_other_attendant_weight').keypress(function(event){
        addWeightedAttendant(event);
    });

    var acceptable_offline_meeting_cities = new Tagify(
        document.querySelector("input[id='id_acceptable_offline_meeting_cities']"),
        {
            userInput: false
        });
    $.getJSON('/static/reunion/world-city.json', function(data) {
        acceptable_offline_meeting_cities.whitelist = data;
    });

    // show and hide method has display issue when options length is too large.
    var options = $("#id_holiday").children('option');
    $("#id_country").val('');
    $("#id_holiday").val('');
    $("#id_country").change(function() {
        $("#id_holiday").empty();
        var className = $(this).val().replace(/\s+/g, '_');
        for (option of options) {
            if (option.getAttribute('class') == className) {
                $("#id_holiday").append(option);
            }
        }
        $("#id_holiday").val('');
        $("#id_holiday").children('option').show();
    });
})
