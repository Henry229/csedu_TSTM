function save_testset() {
    var data = TestsetStageTable.getData();
    var url = $('#branching_form').attr("action");

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
            console.log(response);
            $("#status").show();
            $("#status").html("Testset saved successfully").fadeOut(3000, function () {
                $(this).hide()
            });

        }
    });
}