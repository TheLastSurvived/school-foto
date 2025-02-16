let p = document.getElementById("p");
let h2 = document.getElementById("h2");
let images = document.getElementById("images");

p.addEventListener("click", function (e) {
    text = "<p></p>\n"
    let area = document.getElementById("text_record");
    area.value+=text;
});


h2.addEventListener("click", function (e) {
    text = "<h2></h2>\n"
    let area = document.getElementById("text_record");
    area.value+=text;
});


function processSelectedFiles(fileInput) {
    var files = fileInput.files;
  
    for (var i = 0; i < files.length; i++) {
        let area = document.getElementById("text_record");
        path = "../static/images/blog-img/"
        full_text = path + files[i].name
        area.value+= "<img src="+ full_text + " alt=\"\">\n";
    }
  }