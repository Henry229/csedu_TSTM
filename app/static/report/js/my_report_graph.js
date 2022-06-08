$(function(){
    let arrow1 = $($('.arrow1').get(0));
    if(arrow1.data('percent')!=''){
        let stick1 = $('.ul-standard:eq(1)').position();
        let stick1Left = stick1.left;
        let stick1Top = stick1.top;

        stick1Left = stick1Left - arrow1.width();
        let myScore = parseInt(arrow1.data('percent'));
        //$('.arrow1').offset({ top: myScore * 5, left: stick1Left});


        let top = $('.testset-title').height()+15+500-5 + 245;
        //title:64.8, margin:15, extra:5 + 245
        arrow1.offset({ top: top- (myScore * 5), left: stick1Left});
        arrow1.show();
    }

    let arrow2 = $($('.arrow1').get(1));
    if(arrow2.data('percent')!=''){
        let stick2 = $('.ul-standard:eq(2)').position();
        let stick2Left = stick2.left;
        let stick2Top = stick2.top;

        stick2Left = stick2Left - arrow2.width();
        let myScore = parseInt(arrow2.data('percent'));
        //$('.arrow2').offset({ top: myScore * 5, left: stick2Left});


        let top = $('.testset-title').height()+15+500-5 + 245;
        //title:64.8, margin:15, extra:5 + 245
        arrow2.offset({ top: top- (myScore * 5), left: stick2Left});
        arrow2.show();
    }

    let arrow3 = $($('.arrow1').get(2));
    if(arrow3.data('percent')!=''){
        let stick3 = $('.ul-standard:eq(3)').position();
        let stick3Left = stick3.left;
        let stick3Top = stick3.top;

        stick3Left = stick3Left - arrow3.width();
        let myScore = parseInt(arrow3.data('percent'));
        //$('.arrow3').offset({ top: myScore * 5, left: stick3Left});


        let top = $('.testset-title').height()+15+500-5 + 245;
        //title:64.8, margin:15, extra:5 + 245
        arrow3.offset({ top: top- (myScore * 5), left: stick3Left});
        arrow3.show();
    }

    let arrow4 = $($('.arrow1').get(3));
    if(arrow4.data('percent')!=''){
        let stick4 = $('.ul-standard:eq(4)').position();
        let stick4Left = stick4.left;
        let stick4Top = stick4.top;

        stick4Left = stick4Left - arrow4.width();
        let myScore = parseInt(arrow4.data('percent'));
        //$('.arrow4').offset({ top: myScore * 5, left: stick4Left});


        let top = $('.testset-title').height()+15+500-5 + 245;
        //title:64.8, margin:15, extra:5 + 245
        arrow4.offset({ top: top- (myScore * 5), left: stick4Left});
        arrow4.show();
    }
});