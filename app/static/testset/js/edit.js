function update_testset() {
    var data = {
        'stageData': TestsetStageTable.getData(),
        'testset_id': $('#update_form #testset_id').val(),
        'testset_name': $('#update_form #testset_name').val(),
        'test_type': $('#update_form #test_type').val(),
        'grade': $('#update_form #grade').val(),
        'subject': $('#update_form #subject').val(),
        'no_stages': $('#update_form #no_stages').val(),
        'test_duration': $('#update_form #test_duration').val(),
        'total_score': $('#update_form #total_score').val()
    };

    var url = $('#update_form').attr("action");
    $.ajax({
        url: url,
        method: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        beforeSend: function () {

        },
        complete: function () {

        },
        success: function (response) {
            response = response.replace(/"/g, '');
            $("#status").show();
            $("#status").html("Testset saved successfully").fadeOut(3000, function () {
                $(this).hide();
            });
            window.location.replace(response);
        }
    });
}