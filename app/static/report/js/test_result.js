$(document).ready(function () {
    $("#export-pdf").on("click", function () {
        $("#pdf-download").val(1);
        $("#submit").click();
    });
    $("#export").on("click", function () {
        $("#excel-download").val(1);
        $("#submit").click();
    });
});
