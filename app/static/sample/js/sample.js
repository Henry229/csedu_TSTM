!(function () {
    const e = document.documentElement;
    if ((e.classList.remove("no-js"), e.classList.add("js"), document.body.classList.contains("has-animations"))) {
        const e = (window.sr = ScrollReveal());
        e.reveal(".hero-title, .hero-paragraph, .section-inner-menu, .newsletter-header, .newsletter-form", { duration: 1e3, distance: "40px", easing: "cubic-bezier(0.5, -0.01, 0, 1.005)", origin: "bottom", interval: 150 }),
            e.reveal(".bubble-3, .bubble-4, .hero-browser-inner, .bubble-1, .bubble-2", { duration: 1e3, scale: 0.95, easing: "cubic-bezier(0.5, -0.01, 0, 1.005)", interval: 150 }),
            e.reveal(".feature", { duration: 600, distance: "40px", easing: "cubic-bezier(0.5, -0.01, 0, 1.005)", interval: 100, origin: "bottom", viewFactor: 0.5 });
    }
})();

$(function(){
    $('.tests .feature-menu > .feature-inner-menu').click(function(){
        $('stop[name="stop1"]').attr('stop-color', '#F7F7F7');
        $('stop[name="stop2"]').attr('stop-color', '#E8E8E8');
        $(this).find('linearGradient:first stop[name="stop1"]').attr('stop-color', '#007CFE');
        $(this).find('linearGradient:first stop[name="stop2"]').attr('stop-color', '#007DFF');
        $(this).find('linearGradient:last stop[name="stop1"]').attr('stop-color', '#FF4F7A');
        $(this).find('linearGradient:last stop[name="stop2"]').attr('stop-color', '#FF4F7A');
    });

    $('#sample-apply').click(function(e){
        if($.trim($('#username').val())==''){
            $('#vali-msg').text('please fill out your name');
            $('#vali-msg').css("padding-left", 0);
            $('#vali-msg').fadeIn('slow').delay(1000).fadeOut('slow');
            $('#username').focus();
            return false;
        }
        if(validEmail($.trim($('#useremail').val()))==false){
            $('#vali-msg').text('please check your email');
            //$('#vali-msg').css("padding-left", $('#useremail').offset().left);
            $('#vali-msg').css("padding-left", $('#username').width() + 42);
            $('#vali-msg').fadeIn('slow').delay(1000).fadeOut('slow');
            $('#useremail').focus();
            return false;
        }
    });
});

function validEmail(email) {
    var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(email);
}


