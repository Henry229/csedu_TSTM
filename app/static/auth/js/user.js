$(document).ready(function () {
    toggle_branch_list();
    $('#u_role').on('change', function () {
        toggle_branch_list();
    });
});

function toggle_branch_list() {
    if ($('#u_role').children("option:selected").text()=='Writing_marker') {
        $('.select_branch').show();
    } else {
        $('.select_branch').hide();
    }
}