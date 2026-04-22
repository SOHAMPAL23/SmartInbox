import { motion } from "framer-motion";
import { clsx } from "clsx";

export const MinimalCard = ({ children, className, delay = 0 }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3, ease: "easeOut" }}
      className={clsx(
        "bg-white border border-slate-200 shadow-sm rounded-xl relative overflow-hidden transition-all hover:shadow-md",
        className
      )}
    >
      {children}
    </motion.div>
  );
};
