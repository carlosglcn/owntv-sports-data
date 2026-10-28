var seconde = 10;
var timerId;

var apps = {
    jQuery : $,

    settings : {
        baseUrl : baseUrl,
        siteUrl : appUrl,
		scriptUrl: this.baseUrl+'scripts/'
	},



	/**	******************************************	**
	*	UPLOADIFY
	*	fonctions concernant les uploads avec Uploadify
	**/
	initUploadify : function (params) {
		var params = $.extend({
			controller 	: 'medias',
			action 		: 'ajax_view_picture',
			initImage	: true
		}, params);
		
		if(params.initImage == true){ this.initContent(params);	}
		this.bindUploadify(params);
	},
	bindUploadify: function(params){
		var apps = this,
		$ = this.jQuery,
		settings = this.settings;

		var params = $.extend({
			fileTypeExts 	: '*.jpg; *.gif; *.png; *.jpeg; *.JPG; *.JPEG; *.pdf; *.PDF;',
			fileTypeDesc 	: 'Extensions (.PDF, .JPG, .JPEG, .GIF, .PNG)',
			multi				: true,
			fileWidth 		: 640,
			fileHeight 		: 340,
			thumbWidth 		: 188,
			thumbHeight 	: 100,
			methodUpload : 'move_upload',
			dirUpload 		: 'uploads',
       		buttonClass  : '',
       		buttonText  : 'Ajouter des fichiers',
			fileSizeLimit 	: '200MB',
			onFinish		: 'continue',
			more_params : ''
		}, params);
		

		$('#upl5_button-'+params.name).uploadifive({           
            'uploadScript'          : settings.baseUrl+'ajaxpost1',
            'onUpload' : function() {
                $("#upl5_queue_wrapper-"+params.name).show();
            },           
            'multi'          : params.multi,
            'auto'           : true,
            'fileTypeExts'   : params.fileTypeExts,
            'fileTypeDesc'   : params.fileTypeDesc,
            'queueID'     	 : 'upl5_queue_content-'+params.name,
            'width'          : params.buttonWidth,
            'height'         : params.buttonHeight,
            'fileSizeLimit'  : params.fileSizeLimit,
       		'buttonClass'  	 : params.buttonClass,
       		'buttonText'  	 : params.buttonText,
            'removeCompleted': true,
            'method'         : 'post',
            'formData'          : { 'contents_controller': 'ajax', 'contents_action':'uploadify', 'type': params.type, 'contents_id' : params.contents_id, 'model' : params.model, 'more_params' : params.more_params },
            'onQueueComplete' : function(file, data, response) {
                $("#upl5_queue_wrapper-"+params.name).hide();
               
                if(params.onFinish == "redirect")
                {
                    location.href = params.onFinishUrl;
                } else if(params.onFinish == "functionAfter") {
                    var makeFunction = eval(params.onFinishFunction);
                    makeFunction(params);
		            msg_box = $("#plugin-view-messages-success");
		            msg_box.find(".plugin-view-messages-content").html('Média ajouté');
		            msg_box.fadeIn(500).delay(4000).fadeOut(500);            
                }
            }
        });
	},
	bindDivUploadify: function(params){
		var params = $.extend({
		}, params);

    	$(document).on('click', ".del-file", function(e){
			if(confirm('Supprimer ce fichier ?'))
			{
				$("div#loader-wrapper").show();

				var dataPost = $("#form-"+params.name).serialize()+"&task=del&id="+$(this).attr('id');

				$.ajax({
					type: "POST",
					url: "ajaxpost1",
					data: dataPost,
					success: function(msg){
						$("#target-"+params.name).html(msg);
						$("div#loader-wrapper").hide();
			            msg_box = $("#plugin-view-messages-success");
			            msg_box.find(".plugin-view-messages-content").html('Média supprimé');
			            msg_box.fadeIn(500).delay(4000).fadeOut(500);            
					}
				});
			}
		});
	},

	refreshDivUploadify: function(params){
		var params = $.extend({
		}, params);

		$("div#loader-wrapper").show();

		var dataPost = $("#form-"+params.name).serialize();
		$.ajax({
			type: "POST",
			url: "ajaxpost1",
			data: dataPost,
			success: function(msg){
				$("#target-"+params.name).html(msg);
				$("div#loader-wrapper").hide();
			}
		});		
	},


	/**

	*	CHARGEMENT DE CONTENU DYNAMIQUE
	*	Prise en charge des filtres
	* Prise en charge de la pagination

	**/
	initPluginFilter: function(params){
		var params = $.extend({
			cache: false,
			cacheKeys: []
		}, params);

		$("#loader-wrapper").show();
		apps.bindPluginFilter(params);
		apps.makePluginFilterRequest(params);
	},
	bindPluginFilter: function(params){
		var params = $.extend({
		}, params);

		// Filter actions
    	$(document).on('change', "select", function(e){
    		if(!$(this).hasClass('no-change'))
    		{			
				e.preventDefault();
				$("#loader-wrapper").show();
				apps.makePluginFilterRequest(params);
    		} else if($(this).hasClass('keep-tab')) {
				e.preventDefault();
				$("#loader-wrapper").show();
	            var tab_action = $(this).attr('data-id');
				var params2 = $.extend({
					tmp_action: tab_action
				}, params);
				params2.action = tab_action;
	 			apps.makePluginFilterRequest(params2);
    		}
		});

    	$(document).on('click', ".form-submit", function(e){
			e.preventDefault();
			$("#loader-wrapper").show();
			apps.makePluginFilterRequest(params);
		});
		
       $(document).on('click', ".tabs-button", function(e){
    		if(!$(this).hasClass('no-ajax'))
    		{			
				e.preventDefault();
				$("#loader-wrapper").show();
	            var tab_action = $(this).attr('data-id');
				var params2 = $.extend({
					tmp_action: tab_action
				}, params);
				params2.action = tab_action;
	 			apps.makePluginFilterRequest(params2);
 			}
       });

		// Pagination actions
    	$(document).on('click', ".pagination-bt", function(e){
			$("#loader-wrapper").show();
			var bt_type = this.id;
			var parent = $(this).parents(".pagination-form-wrapper");
			var current = parent.find(".pagination-current").val();

			switch(bt_type)
			{
				case 'page': var next = eval(this.name); break;
				case 'next1': var next = eval(current)+1; break;
				case 'next10': var next = eval(current)+10; break;
				case 'back1': var next = eval(current)-1; break;
				case 'back10': var next = eval(current)-10; break;
			}
			parent.find(".pagination-current").val(next);
			apps.makePluginFilterRequest(params);
		});
		
		// Order actions
    	$(document).on('click', ".order-bt", function(e){
			$("div#loader-wrapper").show();
			var $val = $(this).attr('data-order');
			var parent = $(this).parents(".pagination-form-wrapper");
			var order_field = parent.find("input[name=pagination-order]");
			order_field.val($val);
			apps.makePluginFilterRequest(params);
		});

    	$(document).on('click', ".month-item", function(e){
			$("div#loader-wrapper").show();
			var $value = $(this).attr('id');
			
			$('.months-wrapper-filter').find('option[value="'+$value+'"]').prop('selected', true)
			$('.months-wrapper-filter').selectric('refresh');
									
			$("#current_month").val($value);
			apps.makePluginFilterRequest(params);
		});
		
		$(document).on('change', ".months-wrapper-filter", function(e){
			$("div#loader-wrapper").show();
			var $value = $(this).val();
			$("#current_month").val($value);			
			apps.makePluginFilterRequest(params);
		});
		
    	$(document).on('click', ".letter-item", function(e){
			$("div#loader-wrapper").show();
			var $value = $(this).attr('id');
			$("#current_letters").val($value);
			apps.makePluginFilterRequest(params);
		});
    	$(document).on('keyup', ".type_search", function(e){
	  		var $val = $(".type_search").val();
	  		if($val.length == 0 || $val.length > 2)
	  		{
				$("div#loader-wrapper").show();
				apps.makePluginFilterRequest(params);
	  		}
		});
	},
	makePluginFilterRequest: function(params){
		var params = $.extend({
		}, params);
	
		var dataPost = $("#"+params.form).serialize()+"&contents_controller="+params.controller+"&contents_action="+params.action+"&cache="+params.cache+"&cacheKeys="+params.cacheKeys;
		$.ajax({
			type: "POST",
			url: "ajaxpost1",
			data: dataPost,
			success: function(msg){
				$("div#loader-wrapper").stop().delay(400).hide(10, function(){
					$("#"+params.target).html(msg);
					return true;
				});
			}
		});
	},


	/***
		CALENDARS	 HOME
	**/
	initCalendarsHome:function()
	{
		apps.makeCalendarsHome();
		apps.bindCalendarsHomeActions();
	},
	
	bindCalendarsHomeActions:function()
	{
    	$(document).on('click', ".days-home-wrapper > .arrow", function(e){
			$("div#loader-wrapper").show();
			var id = $(this).attr('id');
			$("#days_id").val(id);
			apps.makeCalendarsHome();
		});
	},

	makeCalendarsHome:function()
	{
		var data = "&contents_controller=sportsCalendars&contents_action=home_ajax&"+$("#calendars-form").serialize();
		$.ajax({
			type: "POST",
			url: "ajaxpost1",
			data: data,
			success: function(msg){
				$("#calendars-home-html").html(msg);
				$("div#loader-wrapper").stop().delay(400).hide(10, function(){
				});
			}
		});		
	},


	initReclamations:function()
	{
		apps.makeReclamations();
		apps.bindReclamationsActions();
	},
	
	bindReclamationsActions:function()
	{
    	$(document).on('change', "#competitions_id", function(e){
            var competitions_id = $(this).val();
            var seasons_id = $("#seasons_id").val();
            var data = "&contents_controller=eReclamations&contents_action=select_index_calendars&competitions_id="+competitions_id+"&seasons_id="+seasons_id;
			apps.makeReclamations(data);
		});
	},

	makeReclamations:function(data)
	{
		$.ajax({
			type: "POST",
			url: "ajaxpost1",
			data: data,
			success: function(msg){
                $("#ajax-target").html(msg);
			}
		});		
	},

	

	/**	******************************************	**
	*	LIVES > INDEX
	**/
	cronRefreshLivesIndexLarge: function(){
		$("div#loader-wrapper").show();
		apps.makeRefreshLivesIndexLarge();
//		setInterval('apps.makeRefreshLivesIndexLarge()', 20000);
		apps.startTimerIndex();
		apps.bindLivesIndexLarge();
	},
	makeRefreshLivesIndexLarge: function(){
		var data = "&contents_controller=eStatsChannels&contents_action=index_ajax&"+$("#lives-form").serialize();
		$.ajax({
			type: "POST",
			url: "ajaxpost1",
			data: data,
			success: function(msg){
				$("#lives-html").html(msg);
				$("div#loader-wrapper").hide();
				return true;
			}
		});		
	},
	bindLivesIndexLarge: function()
	{
    	$(document).on('click', ".settings-state", function(e){
			var value = $(this).attr('id');
			$("#lives_state").val(value);
			$(".settings-state").each(function(){
				$(this).removeClass('is_active');
			});
			$(this).addClass('is_active');
			apps.makeRefreshLivesIndexLarge();
		});
    	$(document).on('click', ".settings-competitions", function(e){
			var value = $(this).attr('id');
			$("#competitions_id").val(value);
			$(".settings-competitions").each(function(){
				$(this).removeClass('is_active');
			});
			$(this).addClass('is_active');
			apps.makeRefreshLivesIndexLarge();
		});
	},

	/**	******************************************	**
	*	LIVES > INDEX > TIMER
	**/
	startTimerIndex: function(){
		timerId = setInterval(function()
			{ apps.timerRemoveIndex()}, 990);
	},
	timerRemoveIndex: function(){
		if(seconde == 1)
		{
			apps.makeRefreshLivesIndexLarge();
			seconde = 11;
		}
		seconde--;
		apps.timerDisplayIndex();
	},
	timerDisplayIndex: function(){
		$("#refresh-timer").html(seconde);
	},


	/**	******************************************	**
	*	LIVES > VIEW
	**/
	cronRefreshLivesViewLarge: function(){
		$("div#loader-wrapper").show();
		apps.makeRefreshLivesViewLarge();
		setInterval('apps.makeRefreshLivesViewLarge()', 11000);
		apps.startTimerView();
		
    	$(document).on('click', ".tabs-button-live", function(e){
			var $id = $(this).attr('id');
			$("#tabs").val($id);
		});
	},
	/*
	makeRefreshLivesViewLarge: function(){
		//var dataPost = $("#live-form").serialize()+"&contents_controller=eStatsChannels&contents_action=view_ajax";
		var dataPost = $("#live-form").serialize()+"&contents_controller=cache&contents_action=render&type=eStatsChannels";
		$.ajax({
			type: "POST",
			url: "ajaxlive",
			data: dataPost,
			success: function(msg){
				$("#live-html").html(msg);
				var $tab = $("#tabs").val();
				$("#"+$tab).addClass('tabs-button-active active');
				$("#content-"+$tab).addClass('tabs-content-active');
				$("div#loader-wrapper").hide();
				return true;
			}
		});
	},
	*/
	makeRefreshLivesViewLarge: function(){
		//var dataPost = $("#live-form").serialize()+"&contents_controller=eStatsChannels&contents_action=view_ajax";
		var dataPost = $("#live-form").serialize();
		$.ajax({
			type: "POST",
			url: "ajaxlive",
			data: dataPost,
			timeout: 10000,
			success: function(msg){
				var liveHtml = $("#live-html");
				if (typeof msg !== 'string' || msg.indexOf('calendars-header') === -1 || msg.indexOf('tabs-content') === -1) {
					apps.showLiveRefreshError();
					return;
				}
				liveHtml.html(msg);
				var $tab = $("#tabs").val();
				var activeButton = liveHtml.find("#"+$tab);
				var activeContent = liveHtml.find("#content-"+$tab);

				// Le fragment mis en cache contient son propre onglet actif. Il faut
				// d'abord le neutraliser avant de restaurer le choix du visiteur.
				if(activeButton.length && activeContent.length)
				{
					liveHtml.find('.tabs-button-live').removeClass('tabs-button-active active');
					liveHtml.find('.tabs-content').removeClass('tabs-content-active').hide();
					activeButton.addClass('active');
					activeContent.addClass('tabs-content-active').show();
				}
				return true;
			},
			error: function(){
				apps.showLiveRefreshError();
			},
			complete: function(){
				$("div#loader-wrapper").hide();
			}
		});
	},
	showLiveRefreshError: function(){
		var liveHtml = $("#live-html");
		if (!liveHtml.find('.live-refresh-status').length) {
			var message = $('<p class="live-refresh-status" role="status"></p>').text('Actualisation du direct momentanément indisponible. Nouvelle tentative automatique dans quelques secondes.');
			if (liveHtml.children().length) {
				liveHtml.prepend(message);
			} else {
				liveHtml.append($('<section class="container"></section>').append(message));
			}
		}
	},


	/**	******************************************	**
	*	LIVES > VIEW > TIMER
	**/
	startTimerView: function(){
		timerId = setInterval(function()
			{ apps.timerRemoveView()}, 990);
	},
	timerRemoveView: function(){
		if(seconde == 1)
		{
			apps.makeRefreshLivesViewLarge();
			seconde = 11;
		}
		seconde--;
		apps.timerDisplayView();
	},
	timerDisplayView: function(){
		$("#refresh-timer").html(seconde);
	},




	/**	******************************************	**
	*	TABS
	*	gestion des tabs (onglets)
	**/
    initTab : function () {
		this.bindTab();
   	},
	bindTab: function(){
       	$(document).on('click', ".tabs-button-live", function(e){
			var tab_parent = $(this).parents(".main-tab-wrapper");
			var tab_name = tab_parent.attr('id');
			
			$("div#loader-wrapper").show();
			
			//	cache l'actuel tab
			var old_tab = tab_parent.find('.tabs-content-active');
			old_tab.removeClass('tabs-content-active');
			old_tab.hide();
			
			//	désactive le bt
			var old_bt = tab_parent.find('.active');
			old_bt.removeClass('active');
			
			//	affiche le nvx tab
			var new_tab = $("#content-"+$(this).attr('id'));
			new_tab.show();
			$("div#loader-wrapper").stop().delay(400).fadeOut();				

			new_tab.addClass('tabs-content-active');
			
			//	active le bt
			var new_bt = $(this);
			new_bt.addClass('active');

			// enregistre en session tab active
			/*
			$.ajax({
				type: "POST",
				url: "ajaxsession",
				data: "session_name="+tab_name+"__tab_active&session_value="+$(this).attr('id'),
				success: function(msg){
				}
			});
			*/
		});
	},

	bindTabForm: function(params){
		var params = $.extend({
			cache: 'no',
			cacheKeys: []
		}, params);

		var button = $("#submit-id-"+params.key);
    	$(document).on('click', "#submit-id-"+params.key, function(e){
			params = $.extend({
				paginate: false
			}, params);
			apps.makeTabs(params);
		});

       	$(document).on('click', ".tabs-button", function(e){
			params = $.extend({
				tab_id: $(this).attr('id'),
				paginate: false
			}, params);
			apps.makeTabs(params);
		});

		var paginate_button = $(".pagination-bt-"+params.key);
    	$(document).on('click', ".pagination-bt-"+params.key, function(e){
			var paginate_tab = {
				paginate: true,
				paginate_bt_type: $(this).attr('id'),
				paginate_bt_name: $(this).attr('name'),
			};			

			params = $.extend(params, paginate_tab);

			apps.makeTabs(params);
		});
	},


	makeTabs: function(params){
		var params = $.extend({
			cache: 'no',
			cacheKeys: []
		}, params);

		$("div#loader-wrapper").show();

		var tab_id = params.tab_id;
		var target = $("#"+params.target);
		var content_tab = $("#content-"+tab_id);
		var form_tab = $("#params-"+tab_id);
		var controller = form_tab.find('input[name=controller]').val();
		var action = form_tab.find('input[name=action]').val();

		if(params.paginate == true)
		{
			var form_content = $("#form-id-"+params.key);
			var current = form_content.find("input[name=pages_current]").val();

			switch(params.paginate_bt_type)
			{
				case 'page': var next = eval(params.paginate_bt_name); break;
				case 'next10': var next = eval(current)+10; break;
				case 'back10': var next = eval(current)-10; break;
			}

			var data = form_tab.serialize()+"&"+$("#form-id-"+params.key).serialize()+"&current_page="+next;
		} else {
			var data = form_tab.serialize()+"&"+$("#form-id-"+params.key).serialize();
		}

		$(target).html();
		$.ajax({
			type: "POST",
			cache: true,
			url: "ajaxpost1",
			data: data+"&contents_controller="+controller+"&contents_action="+action+"&cache="+params.cache+"&cacheKeys="+params.cacheKeys,
			success: function(msg){
				$(target).html(msg);
				$("div#loader-wrapper").stop().delay(400).fadeOut();
				return true;
			}
		});		
	},



	createGraph: function(type, div, data) {
		var function_name = eval(type);
		
		function_name(div, data);
	},
	createCustomGraph: function(type, div, data, params) {
		var function_name = eval(type);

		var params = $.extend({
		}, params);
		
		
		function_name(div, data, params);
	},




	/**	******************************************	**
	*	GLOBALS > FILTRES
	*	filtrage de données
	**/
    initFilter : function () {
		this.bindFilter();
		apps.makeFilterRequest();
   	},
	bindFilter: function(){
		$(".selectFilter").live('change', function(event){
			apps.makeFilterRequest();
		});
	},
	initFilterMobile: function(){
		
    	$(document).on('click', ".filter-mobile-more", function(e){
			if($(".filter-wrapper").css('display')=='block')
			{
				$(".filter-wrapper").slideUp();
			}
			else
			{
				$(".filter-wrapper").slideDown();	
			}
		});
	},
	makeFilterRequest: function(){
		var dataPost = $("#formFilter").serialize();
		apps.makeAjaxPost({'data' : dataPost, 'target': "#contentFilter", 'loader' : 'y'});
	},


	/**	******************************************	**
	*	SHARES
	*	Facebook...
	**/
	initFacebook: function(){
		/*
        window.fbAsyncInit = function(){
            FB.init({
                appId      :'424202661122159',
                status     :true,// vérifier le statut de connexion
                cookie     :true,// autoriser les cookies pour permettre au serveur (et le SDK PHP) d'accéder à la session
                xfbml      :true// analyser le XFBML (déprécié par Facebook, c.f., https://developers.facebook.com/blog/post/568/)
            });
            
            // Ici on s'abonne à l'évènement JavaScript auth.authResponseChange. Cet évènement est généré pour tout 
            // changement dans l'authentification, comme la connexion, la déconnexion, ou le rafraîchissement de la session. 
            // Donc lorsqu'un utilisateur déjà connecté tente se se connecter à nouveau, le cas correct ci-dessous sera géré
            
            FB.Event.subscribe('auth.authResponseChange',function(response){
                // Est-ce que l'utilisateur est connecté au moment où l'évènement est généré ? 
                if(response.status ==='connected'){
                    //console.log("Y'a quelqu'un");
                    // c.f. l'objet response passé en paramète du callback est un objet JSON décrit après ce code.	
                
                
                } else if (response.status ==='not_authorized'){ 
                    // console.log("Y'a quelqu'un, mais il n'est pas connecté à l'application");
                    // Dans ce cas, la personne est loguée Facebook, mais pas à l'application.
                    // Donc on appelle FB.login() pour afficher la boîte de dialogue de connexion à l'application.
                    // On ferait pas comme ça pour une vrai application, pour deux raisons:
                    // (1) Un popup créé automatiquement par JavaScript serait bloqué par la plupart des navigateurs
                    // (2) c'est pas cool de sauter au cou de l'utilisateur dès le chargement de la page comme ça.
                    FB.login();
                }else{
                    // console.log("l'utilisateur n'est pas connecté à Facebook");
                    // Dans ce cas, la personne n'est pas connectée à Facebook. Donc on appelle la méthode login().
                    // A ce moment, on ne sait pas si l'utilisateur s'est déjà connecté à l'application.
                    // si ils ne se sont jamais connecté à l'application, ils verront la boîte de dialogue de connection
                    // à l'application juste après s'être connecté à Facebook.
                    FB.login();
                }
            });
            
        };
                
        // Charger le SDK de manière asynchrone (comme pour les boutons j'aime et partager)
        (function(d){
            var js, id ='facebook-jssdk', ref = d.getElementsByTagName('script')[0];
            if(d.getElementById(id)){return;}
            js = d.createElement('script'); js.id = id; js.async =true;
            js.src ="//connect.facebook.net/fr_FR/all.js";
            ref.parentNode.insertBefore(js, ref);
        }(document));
        */

		window.fbAsyncInit = function() {
			FB.init({
			  appId      : '219021098513358',
			  xfbml      : true,
			  version    : 'v2.8'
			});
		};

		(function(d, s, id){
			 var js, fjs = d.getElementsByTagName(s)[0];
			 if (d.getElementById(id)) {return;}
			 js = d.createElement(s); js.id = id;
			 js.src = "//connect.facebook.net/en_US/sdk.js";
			 fjs.parentNode.insertBefore(js, fjs);
		}(document, 'script', 'facebook-jssdk'));
           
	},
	bindFacebook: function(params){
		$('.'+params.bt).click(function()
		{
			shareFeed();
		});
		function shareFeed()
		{
			FB.ui(
			  {
			   method: 'feed',
			   name: params.name,
			   caption: params.caption,
			   description: (
				  params.description
			   ),
			   link: params.linkurl,
			   picture: params.pictureurl,
	//		   properties : {text:'value1', key2:'value2' },
	//		   actions : {name:'test',link:'https://www.google.fr'}
			  },
			  function(response) {
				if (response && response.post_id) {
	//			  alert('Post was published.');
				} else {
	//			  alert('Post was not published.');
				}
			  }
			);
		}
	},	
	
	/**	******************************************	**
	*	BOX
	*	gestion de la box de connexion
	**/
    initBoxConnect : function () {
		
		this.bindBoxConnect();
   	},
	bindBoxConnect: function(){
		$(document).ready(function() {
			// Vérifier si la tâche "login" est présente dans l'URL
			const urlParams = new URLSearchParams(window.location.search);
			if (urlParams.get('task') === 'login') {
		
				// Ouvrir Fancybox automatiquement
				$("#box_connect").fancybox({
					wrapCSS: 'fancybox-boxconnect',
					fitToView: false,
					autoSize: true,
					type: 'ajax',
					href: 'ajaxpost1',
					ajax: {
						type: "POST",
						data: 'contents_controller=authUsers&contents_action=box_connect_ajax'
					}
				}).trigger("click");
			}
		});
		
		
		$(document).on('click',"#open_box_connect", function(){
			
			$("#box_connect").fancybox({
	           	wrapCSS    		: 'fancybox-boxconnect',
               	fitToView	 	: false,
               	autoSize 		: true,
                type			: 'ajax',
                href 			: 'ajaxpost1',
	            ajax : {
	                type    : "POST",
	                data    : 'contents_controller=authUsers&contents_action=box_connect_ajax'
	            }
	        }).trigger("click");

		});
		
		
		/* OUVERTURE BOX PASSWORD */
		$(document).on('click',"#form_ask_password_page", function(){
		//$("#form_ask_password_page").on('click', function(){
         
            $("#box_connect").fancybox({
            	wrapCSS    		: 'fancybox-boxconnect',
               	fitToView	 	: false,
               	autoSize 		: true,
                type			: 'ajax',
                href 			: 'ajaxpost1',
                ajax : {
                    type    : "POST",
                    data    : 'form_ask_password=1&contents_controller=authUsers&contents_action=box_connect_ajax'
                }
            }).trigger("click");
		});
         
		/* OUVERTURE BOX INSCRIPTION */
		$(document).on('click',"#form_inscription_page", function(){
		//$("#form_inscription_page").on('click',function(){
         
			$("#box_connect").fancybox({
            	wrapCSS    		: 'fancybox-boxconnect',
               	fitToView	 	: false,
               	autoSize 		: true,
                type			: 'ajax',
                href 			: 'ajaxpost1',
                ajax : {
                    type    : "POST",
                    data    : 'form_inscription=1&contents_controller=authUsers&contents_action=box_connect_ajax'
                }
            }).trigger("click");
            
		});
        
        
        /* SOUMISSION FORMULAIRE */
		$(document).on('click',".form_default_submit", function(){
		//$(".form_default_submit").on('click', function(){
        
        	var fields_required = 0;
    		var fields_required_total = 0;
    		
    		var form_current = $(this).parents('form');
    		
    		form_current.find('input').filter('[required]:visible').each(function()
    		{    			
    			fields_required_total = fields_required_total+1;
    			
    			if($(this).val() == '' || $(this).val() == '0')
    			{
    				fields_required = fields_required+1;
    				$(this).addClass('error');
    			}
    			else
    			{
    				$(this).removeClass('error');
    			}
    		});
    		
    		
    		form_current.find('select').filter('[required]:visible').each(function()
    		{
    			fields_required_total = fields_required_total+1;
    		
    			if($(this).val() == '' || $(this).val() == '0')
    			{
    				fields_required = fields_required+1;
    				$(this).addClass('error');
    				$(this).parents('.selectric-wrapper').addClass('error');
    			}
    			else
    			{
    				$(this).removeClass('error');
    				$(this).parents('.selectric-wrapper').removeClass('error');
    			}
    		});
    		    
		
    		if(fields_required > 0 && fields_required <= fields_required_total)
			{
    			msg_box = $("#plugin-view-messages-errors");
                msg_box.find(".plugin-view-messages-content").html("Des champs obligatoires ne sont pas renseignés");
                msg_box.fadeIn(500).delay(4000).fadeOut(500); 
    		}
    		else
    		{   
    			data = form_current.serialize();
            	    	
            	$.ajax({
        			type: "POST",
        			dataType: "json",
        			url: "ajaxpost1",
        			data: data+"&contents_controller=AuthUsers&contents_action=ajax_login&no_render=y",
        			success: function(msg){
        				        				
        				if(msg.is_valid == true)
        				{
        					//msg_box = $("#plugin-view-messages-success");
                            //msg_box.find(".plugin-view-messages-content").html(msg.info);
                            //msg_box.fadeIn(500).delay(4000).fadeOut(500); 
                            
                            location.href = msg.location;
                            
        				}
        				else
        				{
            				msg_box = $("#plugin-view-messages-errors");
                            msg_box.find(".plugin-view-messages-content").html(msg.info);
                            msg_box.fadeIn(500).delay(4000).fadeOut(500); 
                            
                        }
        			}
        		});
    		}
    		
        
        });

		
	},				
}
