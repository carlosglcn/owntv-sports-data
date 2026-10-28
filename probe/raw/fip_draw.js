// Label for the PDF download button.
// PROMISES draws come back with the ACF key as drawType (md_u12, wq_u18, …) and
// are labelled by age class + BOYS/GIRLS, e.g. "BOYS U12 DRAW" / "GIRLS U18 QUALY DRAW".
// Everything else (PRO, BEYOND) keeps the generic PDF Main/Qualy Draw wording.
function getPdfDrawLabel(drawType) {

    var junior = /^(m|w)(d|q)_u(\d{2})$/.exec(drawType || '');

    if (junior) {

        return (junior[1] === 'm' ? 'BOYS' : 'GIRLS')
            + ' U' + junior[3]
            + (junior[2] === 'q' ? ' QUALY' : '')
            + ' DRAW';

    }

    return (drawType == 'MQ' || drawType == 'WQ') ? 'PDF Qualy Draw' : 'PDF Main Draw';

}

// Function to update the API call

function updateAPICall(gender) {

    let drawType = getDrawType(gender);

    let juniorDrawCat = getDrawCat(gender);

    var postID = getCurrentPostID();

    let loader = document.getElementById("loaderDraw");

    let mainDraw = document.getElementById("mainDraw");

    let selectDraw = document.querySelector(".selectDraws");

    let navigators = document.querySelector(".tournamentDraw__navigation");

    loader.style.display = "flex";

    selectDraw.style.zIndex = '4';

    if (navigators) {

      navigators.style.display = "none";

    }

    // AJAX call to the PHP script using POST method

    jQuery.ajax({

      url: ajax_object.ajax_url,

      type: 'POST',

      data: {

        action: 'handle_ajax_request',

        drawType: drawType,

        gender: gender,

        juniorCat: juniorDrawCat,

        postID: postID,

        security: typeof padelfip_ajax !== 'undefined' ? padelfip_ajax.nonce : ''

      },

      beforeSend: function(){

       

      },

      success: function(response) {

        let text = '';

        var res = JSON.parse(response);

        if(res.pdf != ''){          

          jQuery('.drawPDF').attr('href', res.pdf); 

          text = getPdfDrawLabel(res.drawType);

          jQuery('.drawPDF span').text(text);

          jQuery('.drawPDF').show(); 

       

        } else {

          jQuery('.drawPDF').hide();

        }

        if(mainDraw){

          if(res.drawType == 'MQ' || res.drawType == 'WQ'){

            mainDraw.classList.add('qualyDraw');

          } else {

            mainDraw.classList.remove('qualyDraw');

          }

        }

        

        if(res.error == '404'){

          jQuery('#noticeDraw').empty(); 

          jQuery('#noticeDraw').html(res.html); 

          jQuery('#mainDraw').empty(); 

          loader.style.display = "none";

       

        }else{

          jQuery('#noticeDraw').empty(); 

          jQuery('#mainDraw').html(res.html); 

          loadDraw();

          loader.style.display = "none";          
          if (navigators) {
            navigators.style.display = "flex";
          }
       

        }

        /*jQuery('#mainDraw').html(response); 

        loadDraw();

        loader.style.display = "none";

        navigators.style.display = "flex";*/

      },

      complete: function() {

        // handle any error that might occur during the AJAX request 

        selectDraw.style.zIndex = '2';



      }, 

      error: function(){



      }

    });

  }

