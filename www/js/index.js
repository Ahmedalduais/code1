






  $(document).ready(function() {
    var data = {
      "جدول الرقم 1": {
        "1x1": 1,
        "1x2": 2,
        "1x3": 3,
        "1x4": 4,
        "1x5": 5,
        "1x6": 6,
        "1x7": 7,
        "1x8": 8,
        "1x9": 9,
        "1x10": 10,
        "image": "./img/1.svg"
      },
      "جدول الرقم 2": {
        "2x1": 2,
        "2x2": 4,
        "2x3": 6,
        "2x4": 8,
        "2x5": 10,
        "2x6": 12,
        "2x7": 14,
        "2x8": 16,
        "2x9": 18,
        "2x10": 20,
        "image": "./img/2.svg"
      },
      "جدول الرقم 3": {
        "3x1": 3,
        "3x2": 6,
        "3x3": 9,
        "3x4": 12,
        "3x5": 15,
        "3x6": 18,
        "3x7": 21,
        "3x8": 24,
        "3x9": 27,
        "3x10": 30,
        "image": "./img/3.svg"
      },
      "جدول الرقم 4": {
        "4x1": 4,
        "4x2": 8,
        "4x3": 12,
        "4x4": 16,
        "4x5": 20,
        "4x6": 24,
        "4x7": 28,
        "4x8": 32,
        "4x9": 36,
        "4x10": 40,
        "image": "./img/4.svg"
      },
      "جدول الرقم 5": {
        "5x1": 5,
        "5x2": 10,
        "5x3": 15,
        "5x4": 20,
        "5x5": 25,
        "5x6": 30,
        "5x7": 35,
        "5x8": 40,
        "5x9": 45,
        "5x10": 50,
        "image": "./img/5.svg"
      },
      "جدول الرقم 6": {
        "6x1": 6,
        "6x2": 12,
        "6x3": 18,
        "6x4": 24,
        "6x5": 30,
        "6x6": 36,
        "6x7": 42,
        "6x8": 48,
        "6x9": 54,
        "6x10": 60,
        "image": "./img/6.svg"
      },
      "جدول الرقم 7": {
        "7x1": 7,
        "7x2": 14,
        "7x3": 21,
        "7x4": 28,
        "7x5": 35,
        "7x6": 42,
        "7x7": 49,
        "7x8": 56,
        "7x9": 63,
        "7x10": 70,
        "image": "./img/7.svg"
      },
      "جدول الرقم 8": {
        "8x1": 8,
        "8x2": 16,
        "8x3": 24,
        "8x4": 32,
        "8x5": 40,
        "8x6": 48,
        "8x7": 56,
        "8x8": 64,
        "8x9": 72,
        "8x10": 80,
        "image": "./img/8.svg"
      },
      "جدول الرقم 9": {
        "9x1": 9,
        "9x2": 18,
        "9x3": 27,
        "9x4": 36,
        "9x5": 45,
        "9x6": 54,
        "9x7": 63,
        "9x8": 72,
        "9x9": 81,
        "9x10": 90,
        "image": "./img/9.svg"
      },
      "جدول الرقم 10": {
        "10x1": 10,
        "10x2": 20,
        "10x3": 30,
        "10x4": 40,
        "10x5": 50,
        "10x6": 60,
        "10x7": 70,
        "10x8": 80,
        "10x9": 90,
        "10x10": 100,
        "image": "./img/10.svg"
      }
    };
    
  
      // إضافة أزرار لكل جدول
      $.each(data, function(key, value) {
        var imgSrc = value.image; // الحصول على مسار الصورة
        $('#buttons-container').append(
            '<a class="list-button" onclick="showTableData(\'' + key + '\')">' +
            '<div class="item-media" style="display: flex; flex-direction: column; height: 120px;">' +
            '<img style="border-radius: 10px;" src="' + imgSrc + '" width="40px" height="50px">' +
            '<p style="margin-top: auto;">' + key + '</p>' +
            '</div>' +
            '</a>'
        );
    });
  
    var imgX = './img/x.svg';
    var imgEquals = './img/q.svg';
  
    // وظيفة لعرض بيانات الجدول في النافذة المنبثقة
    window.showTableData = function(tableName) {
        var tableData = data[tableName];
        var content = '<ul style="text-align: center; direction: ltr;">';
  
        $.each(tableData, function(key, value) {
            if (key !== "image") { // تجاهل مفتاح الصورة
                var parts = key.split('x');
                var multiplier1 = parts[0];
                var multiplier2 = parts[1];
                var result = value.toString();
  
                // إنشاء عناصر HTML لعرض الصور
                var itemContent = '<li >';
                itemContent += '<img src="./img/' + multiplier1 + '.svg" width="30px" height="40px" style="margin-right: 10px;">';
                itemContent += '<img src="' + imgX + '" width="30px" height="40px" style="margin-right: 10px;">';
                itemContent += '<img src="./img/' + multiplier2 + '.svg" width="30px" height="40px" style="margin-right: 10px;">';
                itemContent += '<img src="' + imgEquals + '" width="30px" height="40px" style="margin-right: 10px;">';
                
                // عرض الأرقام الناتجة كصور
                for (var i = 0; i < result.length; i++) {
                    itemContent += '<img src="./img/' + result[i] + '.svg" width="30px" height="40px"">';
                }
                itemContent += '<hr>';
  
                itemContent += '</li>';
                content += itemContent;
            }
        });
  
        content += '</ul>';
        $('.dynamic-popup .title').text(tableName);
        $('#popup-content').html(content);
        app.popup.open('.dynamic-popup');
    };
  
    
  
  
  
  
    $('#loadButton').click(function() {
      var selectedTable = $('.dynamic-popup .title').text();
      if (!selectedTable) {
          app.toast.create({
              text: 'يرجى اختيار جدول أولاً',
              closeTimeout: 2000,
          }).open();
          return;
      }
    
      var tableData = data[selectedTable];
      var questions = Object.keys(tableData).filter(key => key !== "image"); // استبعاد مفتاح الصورة
      var randomQuestions = [];
      for (var i = 0; i < 10; i++) {
          var randomIndex = Math.floor(Math.random() * questions.length);
          randomQuestions.push(questions[randomIndex]);
          questions.splice(randomIndex, 1);
      }
    
      var currentQuestionIndex = 0;
      var correctAnswers = 0;
      var wrongAnswers = 0;
    
      function showQuestion(index) {
          var question = randomQuestions[index];
          var correctAnswer = tableData[question];
          var wrongAnswersList = [correctAnswer + 1, correctAnswer - 1, correctAnswer + 2].sort(function() { return 0.5 - Math.random(); });
          var allAnswers = [correctAnswer, ...wrongAnswersList].sort(function() { return 0.5 - Math.random(); });
    
          var content = '<div class="list">';
          content += '<div class="card card-outline card-dividers"style="direction: ltr;background-color: white;">' +
              '<div class="card-header">' + formatQuestionAsImage(question) + '</div>' +
              '<div class="card-content card-content-padding">' +
              '<div class="list list-strong-ios list-outline-ios list-dividers-ios">' +
              '<ul>';
          allAnswers.forEach(function(answer) {
              content += '<li style="display: flex;flex-direction: column;align-content: center;flex-wrap: wrap;">' +
                  '<label class="item-radio item-radio-icon-start item-content">' +
                  '<input type="radio" name="question-' + question + '" value="' + answer + '">' +
                  '<i class="icon icon-radio"style="display: none;"></i>' +
                  '<div class="item-inner">' +
                  '<div class="item-title">' + formatAnswerAsImage(answer) + '</div>' +
                  '</div>' +
                  '</label>' +
                 
                  '</li>'+
                  '<hr>';
          });
          content += '</ul></div></div>' +
              '</div>';
          content += '</div>';
    
          $('#popup-contentt').html(content);
    
          // التحقق من الإجابات
          $('input[type="radio"]').change(function() {
              var selectedAnswer = parseInt($(this).val());
              var question = $(this).attr('name').split('-')[1];
              var correctAnswer = tableData[question];
              if (selectedAnswer === correctAnswer) {
                  correctAnswers++;
                  app.toast.create({
                      icon: '<i class="icon f7-icons" style="color: rgb(89, 221, 133);">checkmark_circle_fill</i>',
                      position: 'top',
                      text: 'أحسنت! إجابة صحيحة',
                      closeTimeout: 1000,
                      on: {
                          closed: function() {
                              moveToNextQuestion();
                          }
                      }
                  }).open();
                  new Audio('./img/952.wav').play();
              } else {
                  wrongAnswers++;
                  app.toast.create({
                      icon: '<i class="icon f7-icons" style="color: #e72525;">xmark_circle_fill</i>',
                      position: 'top',
                      text: 'خطأ! حاول مرة أخرى',
                      closeTimeout: 1000,
                      on: {
                          closed: function() {
                              moveToNextQuestion();
                          }
                      }
                  }).open();
                  new Audio('./img/473.wav').play();
              }
          });
      }
    
      function moveToNextQuestion() {
          currentQuestionIndex++;
          if (currentQuestionIndex < randomQuestions.length) {
              showQuestion(currentQuestionIndex);
          } else {
              showResultsDialog();
          }
      }
    
      function showResultsDialog() {
        var evaluation = getEvaluation(correctAnswers); // تحديد التقييم
        var totalQuestions = correctAnswers + wrongAnswers; // إجمالي الأسئلة
        var correctPercentage = (correctAnswers / totalQuestions) * 100; // نسبة الأسئلة الصحيحة بالنسبة المئوية
    
        var dialogContent = '<div class="text-align-center">';
        dialogContent += '<div class="gauge gauge-init" data-type="semicircle" data-value="' + (correctPercentage / 100) + '" data-value-text="' + correctPercentage.toFixed(2) + '%" data-value-text-color="#e91e63" data-border-color="#e91e63" data-label-text="of ' + totalQuestions + ' total" data-label-text-color="#333">';
        dialogContent += '<svg class="gauge-svg" width="200px" height="100px" viewBox="0 0 200 100">';
        dialogContent += '<path class="gauge-back-semi" d="M195,100 a1,1 0 0,0 -190,0" stroke="#eeeeee" stroke-width="10" fill="transparent"></path>';
        dialogContent += '<path class="gauge-front-semi" d="M195,100 a1,1 0 0,0 -190,0" stroke="#e91e63" stroke-width="10" stroke-dasharray="' + (correctPercentage / 100 * 298.45130209103036) + '" stroke-dashoffset="' + ((100 - correctPercentage) / 100 * 298.45130209103036) + '" fill="none"></path>';
        dialogContent += '<text class="gauge-value-text" x="50%" y="100%" font-weight="500" font-size="31" fill="#e91e63" dy="-29" text-anchor="middle" dominant-baseline="false">' + correctPercentage.toFixed(2) + '%</text>';
        dialogContent += '<text class="gauge-label-text" x="50%" y="100%" font-weight="400" font-size="14" fill="#333" dy="-5" text-anchor="middle" dominant-baseline="false">of ' + totalQuestions + ' total</text>';
        dialogContent += '</svg></div>';
        dialogContent += '<div class="chip color-green"><div class="chip-label">الأسئلة الصحيحة: ' + correctAnswers + '</div></div>';
        dialogContent += '<div class="chip color-red"><div class="chip-label">الأسئلة الخاطئة: ' + wrongAnswers + '</div></div>';
        dialogContent += '<div class="gauge-label"style="fontSize: 20px;color: #9cbf06;">' + evaluation + '</div>';
        dialogContent += '</div>';
    
        app.dialog.create({
            title: 'انتهت الأسئلة',
            text: dialogContent,
            buttons: [{
                text: 'حسنًا',
                onClick: function() {
                    // هنا يمكن تنفيذ أي إجراءات أخرى عند إغلاق النافذة
                }
            }]
        }).open();
    }
    
    
      function getEvaluation(correctAnswers) {
          if (correctAnswers >= 9) {
              return 'ممتاز';
          } else if (correctAnswers >= 7) {
              return 'جيد جدًا';
          } else if (correctAnswers >= 5) {
              return 'جيد';
          } else {
              return 'مقبول';
          }
      }
    
      showQuestion(currentQuestionIndex);
      app.popup.open('.dynamic-popup_p');
    });
    
    function formatQuestionAsImage(question) {
      var parts = question.split('x');
      var multiplier1 = parts[0];
      var multiplier2 = parts[1];
      return '<img src="./img/' + multiplier1 + '.svg" width="40px" height="60px">' +
          '<img src="./img/x.svg" width="40px" height="60px">' +
          '<img src="./img/' + multiplier2 + '.svg" width="40px" height="60px">'+
          '<img src="./img/q.svg" width="40px" height="60px">';
    }
    
    function formatAnswerAsImage(answer) {
      var result = answer.toString();
      var images = '';
      for (var i = 0; i < result.length; i++) {
          images += '<img src="./img/' + result[i] + '.svg" width="40px" height="60px">';
      }
      return images;
    }
    });
  

    
  
  
  

  
  
