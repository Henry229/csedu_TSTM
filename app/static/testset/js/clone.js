function clone_testset() {
    var data = {
        'stageData': TestsetStageTable.getData(),
        'testset_id': $('#clone_form #testset_id').val(),
        'testset_name': $('#clone_form #testset_name').val(),
        'test_type': $('#clone_form #test_type').val(),
        'grade': $('#clone_form #grade').val(),
        'subject': $('#clone_form #subject').val(),
        'no_stages': $('#clone_form #no_stages').val(),
        'test_duration': $('#clone_form #test_duration').val(),
        'total_score': $('#clone_form #total_score').val(),
        'link1': $('#clone_form #link1').val()
    };
    var url = $('#clone_form').attr("action");
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