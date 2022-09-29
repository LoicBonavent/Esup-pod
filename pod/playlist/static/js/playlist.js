var showalert = (message, alerttype) => {
  document.body.append(
    `<div id="formalertdiv" class="alert ${alerttype} alert-dismissible fade show" role="alert">${message}<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>`
  );
  setTimeout(() => {
    document.getElementById("formalertdiv").remove();
  }, 5000);
};

var ajaxfail = function (data) {
  showalert(
    gettext("Error getting form.") +
      "(" +
      data +
      ")" +
      gettext("The form could not be recovered."),
    "alert-danger"
  );
};

document.addEventListener("DOMContentLoaded", function () {
  const table = document.getElementById("table_list_videos");

  Array.from(document.querySelectorAll(".position-up")).forEach((element) => {
    element.addEventListener("click", function () {
      let row = element.parentNode.parentNode;

      let currentposition = row.querySelector(".video-position");
      let oldposition = currentposition;
      if (row.previousElementSibling !== null) {
        oldposition =
          row.previousElementSibling.querySelector(".video-position");
      }

      if (currentposition.textContent > 1) {
        currentposition.textContent = parseInt(currentposition.textContent) - 1;
        oldposition.textContent = parseInt(oldposition.textContent) + 1;
      }
      row.parentNode.insertBefore(row, row.previousSibling);
    });
  });

  document.querySelectorAll(".position-down").forEach((element) => {
    element.addEventListener("click", function () {
      let row = element.parentNode.parentNode;
      let currentposition = row.querySelector(".video-position");
      let oldposition = currentposition;
      if (row.nextElementSibling !== null) {
        oldposition = row.nextElementSibling.querySelector(".video-position");
      }

      if (parseInt(currentposition.textContent) < table.rows.length - 1) {
        currentposition.textContent = parseInt(currentposition.textContent) + 1;
        oldposition.textContent = parseInt(oldposition.textContent) - 1;
      }
      row.parentNode.insertBefore(row.nextSibling, row);
    });
  });
  let savePosition = document.getElementById("save-position");
  if (savePosition !== null) {
    savePosition.addEventListener("click", function () {
      var videos = {};
      for (let i = 1; i < table.rows.length; i++) {
        var slug = table.rows[i].children[1].attributes["data-slug"].value;
        var pos = table.rows[i].children[4].innerHTML;
        videos[slug] = pos;
      }
      let token = document.cookie
        .split(";")
        .filter((item) => item.trim().startsWith("csrftoken="))[0]
        .split("=")[1];

      data = JSON.stringify(videos);
      body = JSON.stringify({
        action: "move",
        videos: data,
        csrfmiddlewaretoken: token,
      });

      var jqxhr = fetch(window.location.href, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token,
        },
        body: body,
      })
        .then((response) => {
          if (response.status !== 200) {
            showalert(
              "You are no longer authenticated. Please log in again.",
              "alert-danger"
            );
          } else {
            showalert(response.success, "alert-success");
            window.location.reload();
          }
        })
        .catch((error) => {
          showalert(
            "Error moving videos. (" +
              error +
              ") The videos could not be moved.",
            "alert-danger"
          );
        });
    });
  }

  document.querySelectorAll(".position-delete").forEach((element) => {
    element.addEventListener("click", async function () {
      let slug = element.parentNode.parentNode
        .querySelector(".video-title")
        .getAttribute("data-slug");
      let token = document.cookie
        .split(";")
        .filter((item) => item.trim().startsWith("csrftoken="))[0]
        .split("=")[1];

      headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": token,
      };
      body = {
        video: slug,
        action: "remove",
        csrfmiddlewaretoken: token,
      };

      await fetch(window.location.href, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(body),
      })
        .then((response) => {
          console.log(response.status);

          if (response.status != 200) {
            showalert(
              "You are no longer authenticated. Please log in again.",
              "alert-danger"
            );
          } else {
            showalert(response.statusText, "alert-success");
            window.location.reload();
          }
        })
        .catch((error) => {
          showalert(
            "Error deleting video. (" +
              error +
              ") The video could not be deleted.",
            "alert-danger"
          );
        });
    });
  });

  document.querySelectorAll(".playlist-delete").forEach((element) => {
    element.addEventListener("click", function () {
      let token = document.cookie
        .split(";")
        .filter((item) => item.trim().startsWith("csrftoken="))[0]
        .split("=")[1];
      if (confirm("Are you sure you want to delete this playlist?")) {
        headers = {
          "Content-Type": "application/json",
          "X-CSRFToken": token,
        };
        data = {
          action: "delete",
          csrfmiddlewaretoken: token,
        };
        let jqxhr = fetch(window.location.href, {
          method: "POST",
          headers: headers,
          body: JSON.stringify(data),
        })
          .then((response) => {
            if (response.status != 200) {
              showalert(
                "You are no longer authenticated. Please log in again.",
                "alert-danger"
              );
            } else {
              if (response.status == 200) {
                console.log(response);
                showalert(response.statusText, "alert-success");

                window.location.href = "/playlist/my/";
              } else {
                showalert(response.statusText, "alert-danger");
              }
            }
          })
          .catch((error) => {
            showalert(
              "Error deleting playlist. (" +
                error +
                ") The playlist could not be deleted.",
              "alert-danger"
            );
          });
      }
    });
  });
  let infoVideo = document.getElementById("info-video");
  if (infoVideo !== null) {
    document
      .getElementById("info-video")
      .addEventListener("click", function (e) {
        let target = e.target;
        if (!target.classList.contains("playlist-item")) return;
        e.preventDefault();
        const url = window.location.href;
        const regex = new RegExp("(.*)/video/(\\d+-(.*))/");
        const checkslug = regex.test(url);
        const foundslug = url.match(regex);
        if (!checkslug) {
          showalert(
            gettext("The video can not be added from this page."),
            "alert-danger"
          );
          return;
        }
        if (!foundslug[2]) {
          showalert("The video slug not found.", "alert-danger");
          return;
        }

        const slug = target.getAttribute("data-slug");
        const link = target;
        let token = document.cookie
          .split(";")
          .filter((item) => item.trim().startsWith("csrftoken="))[0]
          .split("=")[1];

        body = JSON.stringify({
          action: "add",
          video: foundslug[2],
          csrfmiddlewaretoken: token,
        });
        const jqxhr = fetch("/playlist/edit/" + slug + "/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": token,
          },
          body: body,
        })
          .then((response) => {
            if (response.status != 200) {
              showalert(
                "You are no longer authenticated. Please log in again.",
                "alert-danger",
                "alert-danger"
              );
            } else {
              if (response.status == 200) {
                showalert(
                  "Video add to playlist",
                  "alert-success",
                  "alert-success"
                );
                link.classList.add("disabled");
                link.classList.remove("playlist-item");
                link.append("");
              }
            }
          })
          .catch((error) => {
            showalert(
              "Error getting video information. (" +
                error +
                ") The video information could not be retrieved.",
              "alert-danger",
              "alert-danger"
            );
          });
      });
  }
});
