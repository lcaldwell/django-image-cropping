var image_cropping = (function ($) {
  var jcrop = {};
  function init() {
    $('input.image-ratio').each(function() {
      var $this = $(this);
      // find the image field corresponding to this cropping value
      // by stripping the last part of our id and appending the image field name
      var field = $this.attr('name').replace($this.data('my-name'), $this.data('image-field'));

      // there should only be one file field we're referencing but in special cases
      // there can be several. Deal with it gracefully.
      var $imageInput = $('input.crop-thumb[data-field-name="' + field + '"]:first');

      var imgSrc;
      // if image doesnt exist already, hide the element, if not get the source name and create and img element from it and initialise jcrop on it.
      if (!$imageInput.length || $imageInput.data('thumbnail-url') === undefined) {
        $this.hide().parents('div.form-row:first').hide();
      } else {
        imgSrc = $imageInput.data('thumbnail-url');
        changeImage($imageInput, $this, imgSrc, false);
      }

      // attach an onChange handler to the file input. after a file change,
      // destroy jcropapi if necessary, destroy previous image if necessary,
      // create an img from the input file, show the crop widget (unless
      // supposed to be hidden) and initialise jcrop on it
      $imageInput.change(function() {
        imgSrc = this.files[0];
        changeImage($imageInput, $this, imgSrc, true);
      });
    });
  }

  function changeImage($imageInput, $ratioInput, imgSrc, imageIsNew) {
    var liOptions = {
      canvas: true,
    }
    loadImage.parseMetaData(imgSrc, function (data) {
      if (data.exif) {
        liOptions.orientation = data.exif.get('Orientation')
      }
      displayImage($imageInput, $ratioInput, imgSrc, imageIsNew, liOptions)
    });
  }

  function displayImage($imageInput, $ratioInput, imgSrc, imageIsNew, liOptions) {
    loadImage(imgSrc, function(imgObj) {
      var imageID = getImageID($ratioInput);

      var imageExists = ($('#' + imageID).length > 0);

      if (imageExists) {
        if (jcrop[imageID] !== undefined) {
          jcrop[imageID].destroy();
        }
        $('#' + imageID).remove();
      }

      var img = new Image();

      // must bind before ataching src attribute
      img.onload = function() {
        if (imageIsNew) {
          setImageInputData($imageInput, $(this));
        }
        $ratioInput.parents('div.form-row:first').show();
        $ratioInput.hide().after($(this).attr('id', imageID));
        var options = buildOptions($imageInput, $ratioInput, imageIsNew);
        initJcrop(imageID, options);
      }

      img.src = imgObj.toDataURL();

    }, liOptions)
  }

  function getImageID($ratioInput) {
    return $ratioInput.attr('id') + '-image';
  }

  function setImageInputData($imageInput, $imgObj) {
    $imageInput.data('org-width', $imgObj[0].width);
    $imageInput.data('org-height', $imgObj[0].height);
  }

  function buildOptions($imageInput, $ratioInput, imageIsNew) {
    var orgWidth = $imageInput.data('org-width'),
        orgHeight = $imageInput.data('org-height'),
        minWidth = $ratioInput.data('min-width'),
        minHeight = $ratioInput.data('min-height');

    if ($ratioInput.data('adapt-rotation') === true) {
      var imageIsPortrait = (orgHeight > orgWidth);
      var selectIsPortrait = (minHeight > minWidth);
      if (imageIsPortrait != selectIsPortrait) {
        // cropping height/width need to be switched, picture is in portrait mode
        var x = minWidth;
        minWidth = minHeight;
        minHeight = x;
      }
    }

    var options = {
      minSize: [5, 5],
      keySupport: false,
      trueSize: [orgWidth, orgHeight],
      onSelect: updateSelection($ratioInput),
      onChange: updateSelection($ratioInput),
      addClass: ($ratioInput.data('size-warning') && ((orgWidth < minWidth) || (orgHeight < minHeight))) ? 'size-warning jcrop-image': 'jcrop-image'
    };
    if ($ratioInput.data('ratio')) {
      options['aspectRatio'] = $ratioInput.data('ratio');
    }
    if ($ratioInput.data('box-max-width')) {
      options['boxWidth'] = $ratioInput.data('box-max-width');
    }
    if ($ratioInput.data('box-max-height')) {
      options['boxHeight'] = $ratioInput.data('box-max-height');
    }

    var initial;
    if (!$ratioInput.val() || imageIsNew) {
      // Initialise the cropping to max possible
      initial = maxCropping(minWidth, minHeight, orgWidth, orgHeight);
      // set cropfield to initial value
      $ratioInput.val(initial.join(','));
    } else {
      initial = valToCrop($ratioInput.val());
    }

    options['setSelect'] = initial;

    return options;
  }

  function initJcrop(imageID, options) {
    $('#' + imageID).Jcrop(options, function(){
      jcrop[imageID] = this;
    });
  }

  function _updateSelection (sel, $cropField) {
    if ($cropField.data('size-warning')) {
      cropIndication(sel, $cropField);
    }
    var sizeString = new Array(
      Math.round(sel.x),
      Math.round(sel.y),
      Math.round(sel.x2),
      Math.round(sel.y2)
    ).join(',');
    $cropField.val(sizeString);
  }

  function updateSelection ($cropField) {
    return function(sel) { _updateSelection(sel, $cropField); };
  }

  function maxCropping (width, height, imageWidth, imageHeight) {
    var ratio = width / height;
    var offset;

    if (imageWidth < imageHeight * ratio) {
      // width fits fully, height needs to be cropped
      offset = Math.round((imageHeight - (imageWidth / ratio)) / 2);
      return [0, offset, imageWidth, imageHeight - offset];
    } else {
      // height fits fully, width needs to be cropped
      offset = Math.round((imageWidth - (imageHeight * ratio)) / 2);
      return [offset, 0, imageWidth - offset, imageHeight];
    }
  }

  function valToCrop (val) {
    if (val === '') { return; }
    var s = val.split(',');
    return [
      parseInt(s[0], 10),
      parseInt(s[1], 10),
      parseInt(s[2], 10),
      parseInt(s[3], 10)
    ];
  }

  function cropIndication (sel, $cropField) {
    // indicate if cropped area gets smaller than the specified minimal cropping
    var $jcropHolder = $cropField.siblings('.jcrop-holder');
    var minWidth = $cropField.data('min-width');
    var minHeight = $cropField.data('min-height');
    if ((sel.w < minWidth) || (sel.h < minHeight)) {
      $jcropHolder.addClass('size-warning');
    } else {
      $jcropHolder.removeClass('size-warning');
    }
  }

  return {
    init: init,
    jcrop: jcrop
  };

})(jQuery);

jQuery(function() {
  var image_cropping_jquery_url = jQuery('.image-ratio:first').data('jquery-url');
  if (image_cropping_jquery_url == "None") {
    // JQUERY_URL is set to `none`. We therefore use the existing version of
    // jQuery and leave it otherwise untouched.
    jQ = jQuery;
  } else {
    // JQUERY_URL is specified. Image Cropping's jQuery is included in no conflict mode,
    jQ = jQuery.noConflict(true);
  }
  jQ(function() {image_cropping.init();});
});
