function search_assessment(year, test_type, test_center) {
    data = {
        "year": year,
        "test_type": test_type,
        "test_center": test_center
    }
    var assessment_obj = $('SELECT[name="assessment"]');
    $.ajax({
        url: '/api/search_assessment/',
        method: 'GET',
        data: data,
        beforeSend: function () {
            assessment_obj.empty()
        },
        complete: function () {

        },
        error: function(xhr, status, error) {
            $("#status").show();
            $("#status").html(xhr.responseText).fadeOut(6000, function () {
                $(this).hide();
            });
        },
        success: function (response) {
            // response.data = [{ 'assessment_guid': '...', 'assessment_name': '...', 'testset_id': '...', 'testset_name': '...'},....] }
            response.data.forEach(function (item) {
                assessment_obj.append(
                    $('<option>', {
                        value: item['assessment_id'] + '_' + item['testset_id'],
                        text: item['assessment_name'] + ' : ' + item['testset_name'] + ' v.' + item['testset_version'],
                    })
                );
            });
        }
    });
}
