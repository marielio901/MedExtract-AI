const input = document.querySelector("#document");
const dropzone = document.querySelector(".upload-dropzone span");

if (input && dropzone) {
  input.addEventListener("change", () => {
    const count = input.files ? input.files.length : 0;
    if (count === 1) {
      dropzone.textContent = input.files[0].name;
    } else if (count > 1) {
      dropzone.textContent = `${count} arquivos selecionados`;
    } else {
      dropzone.textContent = "PDF, JPG, JPEG ou PNG";
    }
  });
}
