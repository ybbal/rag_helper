import pathlib
from telegram import Update
from telegram.ext import ContextTypes


from . import statistic
from . import helpers

async def handle_sberdocs_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    statistic.update_stats(update, context)
    await helpers.forward_to_admin(update, context)
    
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    file_path = project_root / "src" / "instr" / "SberDocs.docx"
    await helpers.send_document(
        update, 
        context, 
        file_path=file_path, 
        user_filename="Инструкция_SberDocs.docx",
        log_intent="СберДокс",
        caption="Ознакомьтесь с подробной инструкцией открыв файл"
    )

async def handle_trip_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    statistic.update_stats(update, context)
    await helpers.forward_to_admin(update, context)
    
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    file_path = project_root / "src" / "instr" / "Инструкция по командировкам.docx"
    await helpers.send_document(
        update, 
        context, 
        file_path=file_path, 
        user_filename="Инструкция по командировкам.docx",
        log_intent="Командировки",
        caption="Ознакомьтесь с подробной инструкцией открыв файл"
    )

async def handle_kprib_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    statistic.update_stats(update, context)
    await helpers.forward_to_admin(update, context)
    
    file_path = pathlib.Path.home() / "rag_helper" / "src" / "instr" / "Барабан.mp4"
    await helpers.send_video(
        update,
        context,
        file_path=file_path,
        user_filename="Барабан.mp4",
        log_intent="кприб",
        caption=""
    )