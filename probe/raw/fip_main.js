function getCurrentPostID() {

	if (typeof ajax_object !== 'undefined' && ajax_object.post_id) {

		return ajax_object.post_id;

	} else {

		return null;

	}

}

/*  ── Global AJAX 403 interceptor + preflight nonce refresh ──
 *  Quando la pagina è servita da LSCache, il nonce in padelfip_ajax.nonce
 *  è quello del momento di generazione cache: può essere scaduto.
 *
 *  Strategia in due livelli:
 *
 *  1. PREFLIGHT (proattivo): all'avvio, se (now - nonce_ts) supera la soglia,
 *     facciamo subito il refresh. I caller che lo desiderano attendono
 *     padelfip_ajax.nonceReady prima del POST, evitando il 403 iniziale.
 *
 *  2. INTERCEPTOR (reattivo): qualunque 403 su admin-ajax.php innesca un
 *     refresh + retry una sola volta, come safety net per cookie scaduto,
 *     race con il preflight, o caller che non usano nonceReady.
 */
(function ($) {
	if (typeof padelfip_ajax === 'undefined') return;

	// Soglia: 11 ore. Il tick nonce WP è 12h (mezza vita 24h), restiamo conservativi.
	var NONCE_MAX_AGE_SEC = 11 * 3600;

	var _refreshing = null; // promise condivisa per evitare N refresh paralleli

	function refreshNonce() {
		if (!_refreshing) {
			_refreshing = $.post(padelfip_ajax.ajax_url, {
				action: 'padelfip_refresh_nonce'
			}).then(function (res) {
				_refreshing = null;
				if (res.success && res.data && res.data.nonce) {
					padelfip_ajax.nonce = res.data.nonce;
					padelfip_ajax.nonce_ts = Math.floor(Date.now() / 1000);
					return res.data.nonce;
				}
				return $.Deferred().reject();
			}, function () {
				_refreshing = null;
				return $.Deferred().reject();
			});
		}
		return _refreshing;
	}

	// Preflight: se il nonce è "stantio" (HTML cachato da molto), refresh subito.
	// nonceReady risolve sempre col nonce attualmente valido.
	var nowSec = Math.floor(Date.now() / 1000);
	var nonceTs = parseInt(padelfip_ajax.nonce_ts, 10) || 0;
	var nonceAge = nowSec - nonceTs;

	if (nonceTs && nonceAge > NONCE_MAX_AGE_SEC) {
		padelfip_ajax.nonceReady = refreshNonce().then(
			function (n) { return n; },
			function () { return padelfip_ajax.nonce; } // fallback: l'interceptor coprirà il 403
		);
	} else {
		padelfip_ajax.nonceReady = $.Deferred().resolve(padelfip_ajax.nonce).promise();
	}

	$(document).ajaxError(function (_event, jqXHR, ajaxSettings) {
		if (jqXHR.status !== 403) return;
		if (ajaxSettings._nonceRetried) return;

		// Solo richieste dirette ad admin-ajax.php
		var url = ajaxSettings.url || '';
		if (url.indexOf('admin-ajax.php') === -1) return;

		ajaxSettings._nonceRetried = true;

		// Aggiorna il nonce nel body della richiesta
		refreshNonce().then(function (freshNonce) {
			var data = ajaxSettings.data || '';

			if (typeof data === 'string') {
				data = data.replace(/security=[^&]*/, 'security=' + encodeURIComponent(freshNonce));
			} else if (typeof data === 'object') {
				data.security = freshNonce;
			}

			$.ajax($.extend({}, ajaxSettings, {
				data: data,
				_nonceRetried: true
			}));
		});
	});
})(jQuery);



jQuery(document).ready(function () {



	// setTimeout(function() {

	var urlParams = new URLSearchParams(window.location.search);

	var tabParam = urlParams.get("tab");

	const tabsArray = jQuery(".tab__item");



	var namesBtnArray = jQuery.map(tabsArray, function (el) {

		var elemJQuery = jQuery(el);

		return elemJQuery.text().trim();

	});

	var check = false; // Variabile per tenere traccia se è stata trovata una corrispondenza



	jQuery.each(namesBtnArray, function (index, el) {

		if (el === tabParam) {

			check = true;

			return false;

		}

	});





	if (!tabParam || !check) {

		const allItemsTab = jQuery(".tab__item");

		const firstItem = allItemsTab.first();



		firstItem.addClass('tab__item--active');

		firstItem.attr('tabindex', 0);

		firstItem.attr('aria-selected', true);

		firstItem.attr('aria-expanded', true);



		const newDataTab = firstItem.attr('data-tab');

		const newDataEl = jQuery('.section__tabsContent .section__itemTabContent[data-tab="' + newDataTab + '"]');



		newDataEl.addClass('section__itemTabContent--active');

		newDataEl.css("display", "block");

		newDataEl.attr('hidden', '');



		//Per pulire l'url se il parametro non esiste

		var url = new URL(window.location.href);

		var params = new URLSearchParams(url.search);



		params.delete("tab");

		url.search = params.toString();

		history.replaceState(null, null, url.toString());





	} else {



		var selectedContent = jQuery('.section__tabsWrapper [aria-selected="true"]').text().trim();



		// Ricerca dell'elemento con il contenuto corrispondente

		var activeItem = jQuery('.tab__item').filter(function () {

			return jQuery(this).text().trim() === selectedContent;

		});



		//Accesso alla classe dell'elemento

		if (activeItem.length > 0) {

			activeItem.removeClass('tab__item--active');

			activeItem.attr('tabindex', -1);

			activeItem.attr('aria-selected', false);

			activeItem.attr('aria-expanded', false);

		}



		let dataTabCurrent = activeItem.attr('data-tab');



		let selectedCurrentContent = jQuery('.section__tabsContent [data-tab="' + dataTabCurrent + '"]');

		selectedCurrentContent.removeClass('section__itemTabContent--active');

		selectedCurrentContent.css("display", "none");

		selectedCurrentContent.attr('hidden', 'hidden');



		///////////////////////////////



		var tabValue = tabParam.substring(); // Ottieni il valore del parametro tab



		// Ricerca dell'elemento con il contenuto corrispondente

		var element = jQuery('.tab__item').filter(function () {

			return jQuery(this).text().trim() === tabValue;

		});



		// Accesso alla classe dell'elemento

		if (element.length > 0) {

			element.addClass('tab__item--active');

			element.attr('tabindex', 0);

			element.attr('aria-selected', true);

			element.attr('aria-expanded', true);

		}



		let newDataTab = element.attr('data-tab');

		let newDataEl = jQuery('.section__tabsContent .section__itemTabContent[data-tab="' + newDataTab + '"]');

		newDataEl.addClass('section__itemTabContent--active');

		newDataEl.css("display", "block");

		newDataEl.attr('hidden', '');

	}



	// Intercepimento del click sugli elementi

	jQuery('[aria-selected]').on('click', function (el) {

		// Aggiornamento dell'URL con il testo del div selezionato

		updateUrl(el);

	});



	function updateUrl(el) {

		let clickedContent = el.target.textContent.trim();



		// Modify the URL with the selected content

		var url = new URL(window.location.href);

		url.searchParams.set('tab', clickedContent);



		// Aggiornamento dell'URL senza ricaricare la pagina

		window.history.replaceState(null, null, url);

	}



	// }, 1000);

});


jQuery(document).ready(function ($) {
	if (typeof Swiper !== 'undefined' && document.getElementById('liveEvents')) {
		new Swiper('#liveEvents', {
			slidesPerView: 2,
			spaceBetween: 20,
			loop: true,
			autoplay: {
				delay: 3000,
				disableOnInteraction: false
			},
			navigation: {
				nextEl: '.loop-live_swiper-relative .swiper-button-next',
				prevEl: '.loop-live_swiper-relative .swiper-button-prev'
			},
			pagination: {
				el: '#liveEvents .swiper-pagination',
				clickable: true
			},
			breakpoints: {
				0: {
					slidesPerView: 1,
					pagination: { el: '#liveEvents .swiper-pagination', clickable: true },
					navigation: false
				},
				769: {
					slidesPerView: 2,
					navigation: {
						nextEl: '.loop-live_swiper-relative .swiper-button-next',
						prevEl: '.loop-live_swiper-relative .swiper-button-prev'
					}
				},
				1281: {
					slidesPerView: 2,
					navigation: {
						nextEl: '.loop-live_swiper-relative .swiper-button-next',
						prevEl: '.loop-live_swiper-relative .swiper-button-prev'
					}
				}
			}
		});
	}

});

function initFancybox() {
	if (window.Fancybox) {
		Fancybox.bind(
			'[data-fancybox="gallery"],a[href*=".jpg"]:not(.f-button),a[href*=".jpeg"]:not(.f-button),a[href*=".png"]:not(.f-button),a[href*=".gif"]:not(.f-button)',
			{
				groupAll: true,
				Toolbar: {
					display: {
						left: [],
						middle: [],
						right: [
							"zoom",
							"slideshow",
							"download",
							"fullscreen",
							"thumbs",
							"close",
						],
					}
				},
			}
		);
	}
}

// Fancybox script is deferred, so it may load after main.js
if (window.Fancybox) {
	initFancybox();
} else {
	window.addEventListener('load', initFancybox);
}



// jQuery(document).ready(function($) {

//     // function renderSliderItems(countries) {
//     //     let html = '';
//     //     countries.forEach(function(country) {
// 	// 		const isActive = (country.id == activeCountryID) ? 'active' : '';
//     //         html += `
//     //             <div class="federations__slide ${isActive}">
// 	// 				<a class="federations__slideLink" href="${country.permalink}" title="${country.nome_stato}" aria-label="Go to ${country.nome_stato}"></a>
//     //                 ${country.bandiera.url ? `<img class="federations__slideFlag" src="${country.bandiera.url}" alt="${country.bandiera.alt}" width="56" height="36" />` : ''}
//     //                 <p class="federations__slideName">${country.nome_stato}</p>
//     //             </div>
//     //         `;
//     //     });
//     //     return html;
//     // }

//     // function initSlider() {
//     //     $('.federations__slider').slick({
//     //         arrows: true,
//     //         infinite: false,
//     //         slidesToShow: 7,
//     //         slidesToScroll: 1,
// 	// 		swipeToSlide: true,
//     //         prevArrow:'<svg class="arrow__left" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path d="M9.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l192 192c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L77.3 256 246.6 86.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-192 192z"/></svg>',
//     //         nextArrow:'<svg class="arrow__right" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path d="M310.6 233.4c12.5 12.5 12.5 32.8 0 45.3l-192 192c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3L242.7 256 73.4 86.6c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l192 192z"/></svg>',
//     //         responsive: [
//     //             { breakpoint: 1440, settings: { slidesToShow: 5 } },
//     //             { breakpoint: 768,  settings: { slidesToShow: 3 } },
//     //             { breakpoint: 420,  settings: { slidesToShow: 1 } }
//     //         ]
//     //     });
//     // }

//     // function loadSlider(continent) {
//     //     const countries = allCountries[continent] || [];

//     //     // Distrugge slick se già inizializzato
//     //     if ($('.federations__slider').hasClass('slick-initialized')) {
//     //         $('.federations__slider').slick('unslick');
//     //     }

//     //     // Inserisce nuove slide e reinizializza slick
//     //     const slidesHtml = renderSliderItems(countries);
//     //     $('.federations__slider').html(slidesHtml);
//     //     initSlider();

//     // }

//     // // Inizializzazione slider con primo continente attivo
//     // const initialContinent = $('.federations__btn.active').data('country');
//     // loadSlider(initialContinent);

//     // // Click su bottoni della nav
//     // $('.federations__btn').on('click', function() {
//     //     const continent = $(this).data('country');

//     //     $('.federations__btn').removeClass('active');
//     //     $(this).addClass('active');

//     //     loadSlider(continent);
//     // });

// });



//inizializzazione degli slider delle nazioni in single-federation
jQuery(document).ready(function ($) {

	if ($('.federations__slider').length && typeof Swiper !== 'undefined') {

		var federationsSwiper = null;

		function renderSliderItems(countries) {
			let html = '';
			countries.forEach(function (country) {
				const isActive = (country.id == activeCountryID) ? 'active' : '';
				html += `
					<div class="swiper-slide federations__slideWrap ${isActive}">
						<div class="federations__slide">
							<a class="federations__slideLink" href="${country.permalink}" title="${country.nome_stato}" aria-label="Go to ${country.nome_stato}"></a>
							${country.bandiera.url ? `<img class="federations__slideFlag" src="${country.bandiera.url}" alt="${country.bandiera.alt}" width="56" height="36" />` : ''}
							<p class="federations__slideName">${country.nome_stato}</p>
						</div>
					</div>
				`;
			});
			return html;
		}

		function loadSlider(continent) {
			const countries = allCountries[continent] || [];
			const $slider = $('.federations__slider');
			const $wrapper = $slider.find('.swiper-wrapper');

			// Nasconde temporaneamente lo slider
			$slider.addClass('is-hidden').removeClass('is-visible');

			// Distrugge istanza Swiper precedente
			if (federationsSwiper) {
				federationsSwiper.destroy(true, true);
				federationsSwiper = null;
			}

			$wrapper.html(renderSliderItems(countries));

			let initialSlideIndex = 0;
			let enableCenterMode = false;

			const $allSlides = $wrapper.children('.federations__slideWrap');
			const $activeSlide = $allSlides.filter('.active');

			if ($activeSlide.length) {
				initialSlideIndex = $allSlides.index($activeSlide);
				if (initialSlideIndex > 2) {
					enableCenterMode = true;
				}
			}

			federationsSwiper = new Swiper('.federations__slider', {
				slidesPerView: 7,
				spaceBetween: 10,
				initialSlide: initialSlideIndex,
				centeredSlides: enableCenterMode,
				navigation: {
					nextEl: '.federations__nav-next',
					prevEl: '.federations__nav-prev'
				},
				breakpoints: {
					0: {
						slidesPerView: 'auto',
						centeredSlides: true
					},
					460: {
						slidesPerView: 2,
						centeredSlides: false
					},
					769: {
						slidesPerView: 3
					},
					1025: {
						slidesPerView: 5
					},
					1441: {
						slidesPerView: 7
					}
				}
			});

			setTimeout(function () {
				$slider.removeClass('is-hidden').addClass('is-visible');
			}, 700);
		}

		// Inizializzazione slider con primo continente attivo
		const initialContinent = $('.federations__btn.active').data('country');
		if (initialContinent) {
			loadSlider(initialContinent);
		} else {
			loadSlider('europe');
		}

		// Click su bottoni della nav
		$('.federations__btn').on('click', function () {
			const continent = $(this).data('country');

			$('.federations__btn').removeClass('active');
			$(this).addClass('active');

			loadSlider(continent);
		});

	}

	// if ($('.federations__nav--single').length) {
	// 	const nav = $('.federations__nav--single');
	// 	const navOffsetTop = nav.offset().top;

	// 	$(window).on('scroll', function () {
	// 		const scrollTop = $(window).scrollTop();

	// 		if (scrollTop >= navOffsetTop - 70) {
	// 			nav.addClass('stuck');
	// 		} else {
	// 			nav.removeClass('stuck');
	// 		}
	// 	});
	// }

	if ($('.federations__nav--single').length) {
		const nav = document.querySelector('.federations__nav--single');
		const trigger = document.querySelector('#nav-trigger');

		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (!entry.isIntersecting) {
						nav.classList.add('stuck');
					} else {
						nav.classList.remove('stuck');
					}
				});
			},
			{
				root: null,
				threshold: 0,
			}
		);

		observer.observe(trigger);
	}

});



document.addEventListener('DOMContentLoaded', function () {

	const federationsSingle = document.querySelector('.federations__nav--single');
	const btotop = document.querySelectorAll(".federations__btn");
	if (federationsSingle) {
		btotop.forEach(element => {
			element.addEventListener('click', function () {
				window.scrollTo({ top: 0, behavior: 'smooth' });
			});
		});
	}



	const buttons = document.querySelectorAll('.federations__btn');
	const federationsArchive = document.querySelector('.federations__nav--archive');
	// const checkboxes = document.querySelectorAll('.tabs input[type="checkbox"]');
	// const labels = document.querySelectorAll('.tab-label');

	if (federationsArchive) {
		buttons.forEach(button => {
			button.addEventListener('click', function (e) {
				e.preventDefault();
				const target = this.dataset.checked;

				// Toggle active class
				buttons.forEach(btn => btn.classList.remove('active'));
				this.classList.add('active');

				// Close all accordions
				// checkboxes.forEach(checkbox => checkbox.checked = false);
				// labels.forEach(label => label.classList.remove('expanded'));

				// Open the matching accordion
				const targetCheckbox = document.getElementById(target);
				if (targetCheckbox) {
					targetCheckbox.checked = true;

					// Add class "expanded" to corresponding label
					const targetLabel = document.querySelector(`label[for="${target}"]`);
					if (targetLabel) {
						targetLabel.classList.add('expanded');
					}

					// Scroll to the accordion smoothly (optional)
					// const targetTab = targetCheckbox.closest('.tab');
					// if (targetTab) {
					//     targetTab.scrollIntoView({ behavior: 'smooth', block: 'start' });
					// }
				}
			});
		});
	}

	const documentsButtons = document.querySelectorAll('.documents__btn');
	const documentsNavArchive = document.querySelector('.documents__nav--archive');
	// const checkboxes = document.querySelectorAll('.tabs input[type="checkbox"]');
	// const labels = document.querySelectorAll('.tab-label');

	if (documentsNavArchive) {
		documentsButtons.forEach(button => {
			button.addEventListener('click', function (e) {
				e.preventDefault();
				const target = this.dataset.checked;

				// Toggle active class
				documentsButtons.forEach(btn => btn.classList.remove('active'));
				this.classList.add('active');

				// Close all accordions
				// checkboxes.forEach(checkbox => checkbox.checked = false);
				// labels.forEach(label => label.classList.remove('expanded'));

				// Open the matching accordion
				const targetDocument = document.getElementById(target);
				if (targetDocument) {
					targetDocument.checked = true;
					targetDocument.scrollIntoView({ behavior: 'smooth', block: 'start' });
					// Scroll to the accordion smoothly (optional)
					// const targetTab = targetCheckbox.closest('.tab');
					// if (targetTab) {
					//     targetTab.scrollIntoView({ behavior: 'smooth', block: 'start' });
					// }
				}
			});
		});

		const observerOptions = {
			root: null,
			rootMargin: '0px 0px -82% 0px',
			threshold: 0
		};

		let documentList = document.querySelectorAll('.items__list');
		const documentsObserver = new IntersectionObserver((entries) => {

			entries.forEach(entry => {
				if (entry.isIntersecting) {
					documentsButtons.forEach(button => {
						button.classList.toggle(
							'active',
							button.getAttribute('href').slice(1) === entry.target.id
						);
					});
				}
			});
		}, observerOptions);

		documentList.forEach(list => {
			if (list) documentsObserver.observe(list);
		});
	}



	const tabsLabel = document.querySelectorAll('.tab-label');

	if (tabsLabel) {
		tabsLabel.forEach(tab => {
			tab.addEventListener('click', () => {
				tab.classList.toggle('expanded');
			})
		});
	}


});